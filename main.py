import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import random
import time
import json
import os
import sys

# Importações do projeto
from classes import EV, Charger
from features import FeatureExtractor
from solver import solve_decision_model
from heuristics import solve_heuristic

# ==========================================
# 1. CONFIGURAÇÕES
# ==========================================
CHECKPOINT_FILE = "adp_checkpoint.json"  # suporte legado
CHECKPOINT_DIR = "checkpoints"
MAX_CHECKPOINT_FILES = 20
STATE_FILE = os.path.join(CHECKPOINT_DIR, "training_state.npz")
CHECKPOINT_INTERVAL = 500
HORIZON = 96            # 24h
TAU = 15                # 15 min
ALPHA = 0.01            # Taxa de aprendizado (Lento e estável)
GAMMA = 0.99            # Fator de desconto
PENALTY = 200.0         # Multa alta

# Preço: Pico entre 17h e 20h
PRICES = [0.50 if (17 <= (t*15)/60 < 20) else 0.15 for t in range(HORIZON)]

# ==========================================
# 2. FUNÇÕES DE PERSISTÊNCIA (SALVAR/CARREGAR)
# ==========================================
def _warn_and_move_corrupted(path):
    corrupted_path = path + ".corrupted"
    os.replace(path, corrupted_path)
    print(f"Aviso: arquivo de checkpoint corrompido movido para {corrupted_path}")
    return corrupted_path


def _load_training_state():
    if not os.path.exists(STATE_FILE):
        return None

    try:
        with np.load(STATE_FILE) as data:
            iteration = int(data["iteration"])
            zetas = np.array(data["zetas"])
            history = [np.array(row) for row in np.atleast_2d(data["history"])]
    except Exception:
        _warn_and_move_corrupted(STATE_FILE)
        return None

    return {
        "zetas": zetas,
        "iteration": iteration,
        "history": history
    }


def _load_legacy_checkpoint():
    if not os.path.exists(CHECKPOINT_FILE) or os.path.isdir(CHECKPOINT_FILE):
        return None

    try:
        with open(CHECKPOINT_FILE, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        _warn_and_move_corrupted(CHECKPOINT_FILE)
        return None

    history = data.get("history", []) or [data.get("zetas", [])]
    history = [np.array(z) for z in history]

    result = {
        "zetas": np.array(data["zetas"]),
        "iteration": data["iteration"],
        "history": history
    }

    # Migra o formato legado para o novo esquema de checkpoints.
    save_checkpoint(result["zetas"], result["iteration"])
    save_training_state(result["zetas"], result["iteration"], result["history"])
    os.remove(CHECKPOINT_FILE)

    return result


def _list_checkpoint_files():
    if not os.path.isdir(CHECKPOINT_DIR):
        return []
    files = [
        os.path.join(CHECKPOINT_DIR, name)
        for name in os.listdir(CHECKPOINT_DIR)
        if name.endswith('.json')
    ]
    files.sort()
    return files


def save_training_state(zetas, iteration, history):
    if not history:
        return

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    hist_arr = np.stack(history)
    tmp_path = os.path.join(CHECKPOINT_DIR, "training_state.tmp.npz")
    np.savez_compressed(
        tmp_path,
        iteration=np.array(iteration, dtype=np.int64),
        zetas=np.array(zetas),
        history=hist_arr
    )
    os.replace(tmp_path, STATE_FILE)


def save_checkpoint(zetas, iteration):
    """Salva o cérebro da IA em checkpoints atômicos e rotativos."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    if os.path.exists(CHECKPOINT_FILE) and not os.path.isdir(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

    filename = f"checkpoint_{iteration:08d}.json"
    tmp_path = os.path.join(CHECKPOINT_DIR, filename + '.tmp')
    final_path = os.path.join(CHECKPOINT_DIR, filename)

    data = {
        "iteration": iteration,
        "zetas": zetas.tolist()
    }

    with open(tmp_path, 'w') as f:
        json.dump(data, f)

    os.replace(tmp_path, final_path)

    # Limita a quantidade de arquivos para evitar uso excessivo de disco.
    files = _list_checkpoint_files()
    while len(files) > MAX_CHECKPOINT_FILES:
        os.remove(files.pop(0))


def load_checkpoint():
    """Carrega o cérebro da IA do disco."""
    state = _load_training_state()
    if state:
        return state

    legacy = _load_legacy_checkpoint()
    if legacy:
        return legacy

    files = _list_checkpoint_files()
    if not files:
        return None

    history = []
    latest = None
    for path in files:
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            _warn_and_move_corrupted(path)
            continue

        zetas = np.array(data["zetas"])
        history.append(zetas)

        if latest is None or data["iteration"] > latest["iteration"]:
            latest = {"iteration": data["iteration"], "zetas": zetas}

    if latest is None:
        return None

    save_training_state(latest["zetas"], latest["iteration"], history)

    return {
        "zetas": latest["zetas"],
        "iteration": latest["iteration"],
        "history": history
    }

# ==========================================
# 3. SIMULAÇÃO (MOTOR)
# ==========================================
def get_base_scenario():
    chargers = [Charger(1, 22.0, 2, False), Charger(2, 50.0, 1, True)]
    evs = [EV(1, 0, 32, 40.0, 40.0), EV(2, 0, 90, 60.0, 60.0)]
    return evs, chargers

def run_day(strategy, zetas=None, training=False):
    evs, chargers = get_base_scenario()
    
    total_cost = 0.0
    total_energy = 0.0
    total_req = sum(e.required_energy for e in evs)
    
    load_profile = np.zeros(HORIZON)
    feats_hist = []
    step_costs = []
    cpu_times = []
    
    extractor = FeatureExtractor(TAU)

    for t in range(HORIZON):
        # Chegadas
        new_evs = []
        if training:
            if random.random() < 0.15:
                new_evs.append(EV(len(evs)+100, t, min(96, t+35), 30.0, 30.0))
        elif t == 68: # Teste às 17:00
            new_evs.append(EV(200, t, 92, 45.0, 45.0))
            
        evs.extend(new_evs)
        if not training: total_req += sum(e.required_energy for e in new_evs)

        # Features
        if strategy == 'ADP' or training:
            feats_hist.append(extractor.get_basis_functions(evs, chargers, t))

        # Decisão
        start = time.time()
        if strategy == 'ADP':
            decs, _ = solve_decision_model(evs, chargers, t, PRICES[t], zetas, TAU)
        else:
            decs = solve_heuristic(evs, chargers, strategy, TAU)
        cpu_times.append(time.time() - start)

        # Física
        step_c = 0.0
        step_e = 0.0
        for c in chargers: c.connected_evs = {} 

        for d in decs:
            charger = next(c for c in chargers if c.id == d['charger_id'])
            charger.connected_evs[d['connector_id']] = d['ev_id']
            ev = next(e for e in evs if e.id == d['ev_id'])
            energy = min(d['charge_rate']*(TAU/60.0), ev.current_energy_needed)
            ev.current_energy_needed -= energy
            ev.assigned_charger_id = d['charger_id']
            step_c += energy * PRICES[t]
            step_e += energy
            
        # Penalidade
        for ev in evs:
            if ev.departure_time == t and ev.current_energy_needed > 0.1:
                step_c += ev.current_energy_needed * PENALTY

        total_cost += step_c
        total_energy += step_e
        load_profile[t] = step_e
        step_costs.append(step_c)
        evs = [e for e in evs if e.departure_time > t]

    sl = (total_energy / total_req * 100) if total_req > 0 else 100
    avg_cpu = sum(cpu_times)/len(cpu_times) if cpu_times else 0
    
    return {'cost': total_cost, 'sl': sl, 'load': load_profile, 
            'feats': feats_hist, 'step_costs': step_costs, 'cpu': avg_cpu}

# ==========================================
# 4. FUNÇÃO DE PLOTAGEM (FINALIZAÇÃO)
# ==========================================
def generate_final_report(zetas, zeta_history):
    print("\n>>> Gerando Relatórios e Gráficos...")
    
    # Testes Comparativos
    adp = run_day('ADP', zetas)
    edld = run_day('EDLD')
    
    print(f"ADP  -> Custo: ${adp['cost']:.2f} | Nível Serviço: {adp['sl']:.1f}%")
    print(f"EDLD -> Custo: ${edld['cost']:.2f} | Nível Serviço: {edld['sl']:.1f}%")

    # Fig 3: Convergência
    plt.figure(figsize=(12,5))
    if len(zeta_history) > 0:
        plt.plot(zeta_history)
        plt.legend(['Bias','Sched','Conn','Rem','Urg','Time'])
        plt.title(f'Convergência dos Pesos ({len(zeta_history)} iterações)')
        plt.grid(alpha=0.3)
        plt.savefig('fig3_convergencia.png')

    # Fig 9: Perfil de Carga
    hours = np.arange(HORIZON) * 15/60
    fig, ax1 = plt.subplots(figsize=(10,6))
    ax2 = ax1.twinx()
    ax2.step(hours, PRICES, color='red', where='post', label='Preço', linewidth=2)
    ax2.set_ylabel('Preço ($)', color='red')
    ax2.set_ylim(0, 0.6)
    
    ax1.bar(hours-0.2, adp['load'], width=0.2, color='blue', label='ADP (IA)')
    ax1.bar(hours+0.2, edld['load'], width=0.2, color='gray', label='EDLD (Regra)', alpha=0.5)
    
    ax1.set_title('Perfil de Carga: ADP vs EDLD')
    ax1.legend(loc='upper left')
    plt.savefig('fig9_perfil_carga.png')
    
    # Fig Dashboard (Resumo)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10,5))
    ax1.bar(['ADP','EDLD'], [adp['cost'], edld['cost']], color=['blue','gray'])
    ax1.set_title('Custo Total ($)')
    ax2.bar(['ADP','EDLD'], [adp['sl'], edld['sl']], color=['green','orange'])
    ax2.axhline(100, color='red', linestyle='--')
    ax2.set_title('Nível de Serviço (%)')
    plt.savefig('fig_dashboard.png')
    
    print("\n=== PROCESSO FINALIZADO COM SUCESSO ===")
    print("Gráficos salvos na pasta atual.")

# ==========================================
# 5. LOOP PRINCIPAL COM MENU
# ==========================================
def main():
    print("=== SISTEMA DE TREINAMENTO CONTÍNUO ADP ===")
    
    current_zetas = np.zeros(6)
    current_zetas[3] = 10.0 # Inicialização padrão
    zeta_history = []
    iteration_count = 0
    
    # Verificar Checkpoint
    checkpoint = load_checkpoint()
    
    if checkpoint:
        print(f"\nCheckpoint encontrado! Iteração atual: {checkpoint['iteration']}")
        print(f"Últimos Zetas: {np.round(checkpoint['zetas'], 2)}")
        print("\nO que você deseja fazer?")
        print("  [C] Continuar Treinamento (Carregar dados)")
        print("  [R] Reiniciar (Apagar dados e começar do zero)")
        print("  [F] Finalizar Agora (Gerar gráficos com o que já aprendeu)")
        
        choice = input("Escolha: ").upper()
        
        if choice == 'C':
            current_zetas = checkpoint['zetas']
            iteration_count = checkpoint['iteration']
            zeta_history = checkpoint['history']
            print(f"\n>>> Retomando da iteração {iteration_count}...")
            
        elif choice == 'F':
            current_zetas = checkpoint['zetas']
            zeta_history = checkpoint['history']
            generate_final_report(current_zetas, zeta_history)
            return # Sai do programa
            
        else:
            print("\n>>> Iniciando NOVO treinamento do zero...")
            # Mantém os valores padrão definidos no início do main
    
    else:
        print("\nNenhum checkpoint encontrado. Iniciando novo treinamento.")

    # LOOP INFINITO DE TREINO
    print("\n>>> TREINAMENTO INICIADO (Pressione Ctrl+C para pausar/menu)")
    time.sleep(2) # Pausa dramática
    
    try:
        while True:
            iteration_count += 1
            
            # 1. Roda o dia
            res = run_day('ADP', current_zetas, training=True)
            zeta_history.append(current_zetas.copy())
            
            # 2. Calcula V_hat
            v_hat = []
            for t in range(HORIZON):
                fut = 0
                disc = 1.0
                for k in range(t, HORIZON):
                    fut += disc * res['step_costs'][k]
                    disc *= GAMMA
                v_hat.append(fut)
            
            # 3. Regressão e Atualização
            reg = LinearRegression(fit_intercept=False)
            reg.fit(res['feats'], v_hat)
            current_zetas = (1 - ALPHA) * current_zetas + ALPHA * reg.coef_
            
            # 4. Log e Salvamento
            if iteration_count % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(current_zetas, iteration_count)
                save_training_state(current_zetas, iteration_count, zeta_history)
                
            print(f"Iter {iteration_count}: Custo={res['cost']:.2f} | Zeta_Carga={current_zetas[3]:.2f}")

    except KeyboardInterrupt:
        print("\n\n>>> TREINAMENTO PAUSADO PELO USUÁRIO <<<")
        print(f"Estado salvo na iteração {iteration_count}.")
        
        choice = input("\nDeseja [F]inalizar e gerar gráficos ou apenas [S]air? (F/S): ").upper()
        if choice == 'F':
            generate_final_report(current_zetas, zeta_history)
        else:
            print("Até logo! Pode retomar depois rodando o script novamente.")

if __name__ == "__main__":
    main()