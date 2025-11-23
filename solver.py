import pyomo.environ as pyo

def solve_decision_model(evs, chargers, current_epoch, energy_price, zetas, tau=15):
    # 1. Prepara atribuições possíveis
    possible_assignments = []
    for charger in chargers:
        for k in range(charger.num_connectors):
            for ev in evs:
                if ev.current_energy_needed > 0.001: 
                    possible_assignments.append((charger.id, k, ev.id))

    # Proteção contra lista vazia
    if not possible_assignments:
        return [], 0.0

    model = pyo.ConcreteModel()
    model.A = pyo.Set(initialize=possible_assignments, dimen=3)
    
    # Variáveis
    model.x = pyo.Var(model.A, domain=pyo.Binary)
    model.q = pyo.Var(model.A, domain=pyo.NonNegativeReals)

    # --- Restrições ---
    
    # C1: Um EV por conector
    def rule_one_ev(model, i, k):
        idxs = [idx for idx in model.A if idx[0]==i and idx[1]==k]
        if not idxs: return pyo.Constraint.Skip
        return sum(model.x[idx] for idx in idxs) <= 1
    model.c1 = pyo.Constraint(set((i,k) for i,k,j in model.A), rule=rule_one_ev)

    # C2: Um Conector por EV
    def rule_one_conn(model, j):
        idxs = [idx for idx in model.A if idx[2]==j]
        return sum(model.x[idx] for idx in idxs) <= 1
    model.c2 = pyo.Constraint(set(j for i,k,j in model.A), rule=rule_one_conn)

    # C3: Potência Máxima
    def rule_max_p(model, i, k, j):
        charger = next(c for c in chargers if c.id == i)
        return model.q[i,k,j] <= charger.max_power * model.x[i,k,j]
    model.c3 = pyo.Constraint(model.A, rule=rule_max_p)

    # C4: Demanda Restante (Física)
    def rule_demand(model, i, k, j):
        ev = next(e for e in evs if e.id == j)
        return model.q[i,k,j] * (tau/60.0) <= ev.current_energy_needed
    model.c4 = pyo.Constraint(model.A, rule=rule_demand)

    # --- Função Objetivo (ADP) ---
    
    # Custo Imediato
    cost_now = sum(energy_price * model.q[idx] * (tau/60.0) for idx in model.A)

    # Features reconstruídas com variáveis
    f_sched = sum(model.x[idx] for idx in model.A)
    
    total_conn = sum(c.num_connectors for c in chargers)
    f_avail = total_conn - f_sched
    
    total_dem = sum(ev.current_energy_needed for ev in evs)
    energy_delivered_now = sum(model.q[idx] * (tau/60.0) for idx in model.A)
    f_rem = total_dem - energy_delivered_now
    
    f_urg = 0
    for ev in evs:
        if ev.departure_time > current_epoch:
            urg = 1.0 / (ev.departure_time - current_epoch)
            is_conn = sum(model.x[idx] for idx in model.A if idx[2] == ev.id)
            f_urg += urg * (1 - is_conn)
            
    # Feature de tempo normalizada igual ao features.py
    total_min = 96 * tau
    f_time = (current_epoch * tau) / total_min

    # Valor Futuro Aproximado
    vfa = (zetas[0] + 
           zetas[1]*f_sched + 
           zetas[2]*f_avail + 
           zetas[3]*f_rem + 
           zetas[4]*f_urg + 
           zetas[5]*f_time)

    model.obj = pyo.Objective(expr=cost_now + vfa, sense=pyo.minimize)

    # Solver
    solver = pyo.SolverFactory('glpk')
    solver.solve(model)

    decisions = []
    for (i, k, j) in model.A:
        if pyo.value(model.x[i,k,j]) > 0.5:
            decisions.append({
                'charger_id': i, 'connector_id': k, 'ev_id': j,
                'charge_rate': pyo.value(model.q[i,k,j])
            })
            
    return decisions, pyo.value(model.obj)