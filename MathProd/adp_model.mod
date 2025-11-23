# ==============================================================================
# 1. CONJUNTOS (SETS) E PARÂMETROS (DADOS)
# ==============================================================================

# Conjuntos básicos
set CHARGERS;         # [cite_start]Conjunto de carregadores (i) [cite: 173]
set EVS;              # [cite_start]Conjunto de veículos presentes (j) [cite: 166]
set CONNECTORS{i in CHARGERS}; # [cite_start]Conectores de cada carregador (k) [cite: 187]

# Parâmetros do Sistema
param Tau := 15;            # [cite_start]Duração da época em minutos [cite: 165]
param MaxPower{i in CHARGERS}; # [cite_start]u_i: Potência máx do carregador (kW) [cite: 175]
param GridLimit := 1000;    # [cite_start]U: Limite total da rede (kW) [cite: 194]
param EnergyPrice;          # [cite_start]e_t: Preço da energia agora [cite: 160]

# Dados dos Veículos
param EnergyNeeded{j in EVS}; # [cite_start]d_jt: Carga necessária atual (kWh) [cite: 172]
param UrgencyScore{j in EVS}; # 1/(delta_j - t): Pré-calculado para simplificar

# Pesos do ADP (Aprendidos na Regressão) - Os famosos "Zetas"
param Zeta{0..5};           [cite_start]# [cite: 491-495]
param CurrentTimeFeature;   # phi_5 (Tau * t)

# ==============================================================================
# 2. VARIÁVEIS DE DECISÃO
# ==============================================================================

# X[i,k,j]: 1 se o veículo j conectar no carregador i, conector k
# [cite_start]Eq (33): Variável binária [cite: 554]
var X{i in CHARGERS, k in CONNECTORS[i], j in EVS} binary;

# Q[i,k,j]: Taxa de carga (kW) fornecida
# [cite_start]Eq (35): Variável contínua não-negativa [cite: 557]
var Q{i in CHARGERS, k in CONNECTORS[i], j in EVS} >= 0;

# ==============================================================================
# 3. FUNÇÃO OBJETIVO (ADP)
# ==============================================================================

# O objetivo é minimizar: Custo Imediato + Valor Futuro Aproximado (VFA)
# [cite_start]Eq (21) e (22) do artigo [cite: 487-495]

minimize Total_Cost:
    # --- Parte A: Custo Imediato ---
    # Soma de (Preço * Energia Entregue)
    sum{i in CHARGERS, k in CONNECTORS[i], j in EVS} 
        (EnergyPrice * Q[i,k,j] * (Tau/60))

    + # Mais...

    # --- Parte B: Função de Valor Aproximada (VFA) ---
    (
      Zeta[0] * 1 +  # Bias

      # Feature 1: Número de VEs agendados (Soma de X)
      Zeta[1] * (sum{i in CHARGERS, k in CONNECTORS[i], j in EVS} X[i,k,j]) +

      # Feature 2: Conectores Disponíveis (Total - Soma de X)
      Zeta[2] * (
          (sum{i in CHARGERS} card(CONNECTORS[i])) - 
          (sum{i in CHARGERS, k in CONNECTORS[i], j in EVS} X[i,k,j])
      ) +

      # Feature 3: Carga Restante Futura (Demanda Total - Energia Entregue Agora)
      Zeta[3] * (
          (sum{j in EVS} EnergyNeeded[j]) - 
          (sum{i in CHARGERS, k in CONNECTORS[i], j in EVS} Q[i,k,j] * (Tau/60))
      ) +

      # Feature 4: Urgência dos NÃO agendados
      # Se conectado (sum X = 1), urgência zera. Se não (sum X = 0), soma a urgência.
      Zeta[4] * (
          sum{j in EVS} (
              UrgencyScore[j] * (1 - sum{i in CHARGERS, k in CONNECTORS[i]} X[i,k,j])
          )
      ) +

      # Feature 5: Tempo (Constante nesta iteração)
      Zeta[5] * CurrentTimeFeature
    );

# ==============================================================================
# 4. RESTRIÇÕES (CONSTRAINTS)
# ==============================================================================

# [cite_start]Eq (23): Cada conector atende no máximo 1 veículo [cite: 498]
subject to One_EV_Per_Connector {i in CHARGERS, k in CONNECTORS[i]}:
    sum{j in EVS} X[i,k,j] <= 1;

# [cite_start]Eq (24): Cada veículo se conecta a no máximo 1 carregador [cite: 501]
subject to One_Connector_Per_EV {j in EVS}:
    sum{i in CHARGERS, k in CONNECTORS[i]} X[i,k,j] <= 1;

# [cite_start]Eq (26) e (29): Limite de potência do carregador e Lógica de Conexão [cite: 507, 520]
# Só pode fornecer energia (Q) se estiver conectado (X=1)
# E não pode passar da potência máxima (u_i)
subject to Max_Charger_Power {i in CHARGERS, k in CONNECTORS[i], j in EVS}:
    Q[i,k,j] <= MaxPower[i] * X[i,k,j];

# [cite_start]Eq (30): Limite total da rede elétrica [cite: 523]
subject to Grid_Capacity_Limit:
    sum{i in CHARGERS, k in CONNECTORS[i], j in EVS} Q[i,k,j] <= GridLimit;

# Restrição Lógica Extra (Não está explícita como eq numerada, mas implícita na lógica):
# Não entregar mais energia do que o veículo precisa
subject to Demand_Satisfaction {i in CHARGERS, k in CONNECTORS[i], j in EVS}:
    Q[i,k,j] * (Tau/60) <= EnergyNeeded[j];

end;