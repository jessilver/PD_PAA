# Validação Matemática do Modelo ADP (MathProg/GLPK)

Este diretório contém a implementação "pura" e independente do modelo de decisão utilizado no projeto de gerenciamento de carregamento de VEs. O modelo é escrito em **MathProg (GMPL)**, a linguagem de modelagem nativa do solver GLPK.

O objetivo deste módulo é permitir a validação, depuração e inspeção do modelo matemático fora do ambiente Python/Pyomo, garantindo que as restrições e a função objetivo estejam matematicamente corretas.

## 📐 Abordagem Matemática

O problema de decisão resolvido a cada época ($t$) é classificado como um problema de **Programação Linear Inteira Mista (MILP - Mixed-Integer Linear Programming)**.

### Por que MILP?

A escolha por MILP se justifica pela natureza híbrida das decisões que o sistema precisa tomar simultaneamente:

1.  **Decisões Discretas (Inteiras/Binárias):** Determinar *qual* veículo conectar a *qual* carregador. Isso exige variáveis binárias ($0$ ou $1$) para garantir exclusividade (um carro por plugue).
2.  **Decisões Contínuas:** Determinar a *taxa de carga* (potência em kW) a ser enviada. Isso exige variáveis contínuas reais não-negativas.

### O Papel da Programação Dinâmica Aproximada (ADP)

Embora o solver resolva um problema determinístico (MILP), a inteligência estocástica do ADP é inserida na **Função Objetivo**.

  * Em vez de apenas minimizar o custo atual (o que seria míope), o modelo minimiza:
    $$\text{Min } ( \text{Custo Imediato} + \text{Valor Futuro Estimado} )$$
  * O "Valor Futuro" é uma aproximação linear ($\sum \zeta_f \phi_f$) aprendida via regressão. Isso transforma um problema estocástico complexo (incerteza do futuro) em um problema determinístico que o GLPK consegue resolver em milissegundos.

-----

## 📂 Estrutura dos Arquivos

  - **`adp_model.mod` (O Modelo):** Declaração algébrica do problema.
      - Define as variáveis binárias de conexão `X[i,k,j]`.
      - Define as variáveis contínuas de potência `Q[i,k,j]`.
      - Implementa as restrições físicas (capacidade do carregador, balanço de energia, um carro por conector).
      - Contém a função objetivo expandida com os pesos `Zeta` aprendidos.
  - **`dados.dat` (O Cenário):** Representa um "snapshot" (foto instantânea) do sistema em um momento específico.
      - Contém os parâmetros de entrada: estado da bateria (`EnergyNeeded`), urgência calculada (`UrgencyScore`), preços atuais e o vetor de pesos `Zeta` (extraído do treinamento em Python).
  - **`solution.sol` (O Resultado):** Arquivo de saída gerado pelo GLPK contendo a solução ótima para a instância fornecida.

## 🚀 Como Rodar

Certifique-se de ter o pacote `glpk-utils` instalado no seu sistema. No terminal, dentro desta pasta, execute:

```bash
glpsol -m adp_model.mod -d dados.dat -o solution.sol
```

Isso compila o modelo, carrega os dados do cenário, resolve o MILP e grava os resultados detalhados em `solution.sol`.

## 🔍 Observações de Implementação

Ao traduzir cenários do Python para o MathProg, atente-se aos seguintes detalhes para manter a consistência numérica:

1.  **Normalização do Tempo (`phi_5`):** O parâmetro `CurrentTimeFeature` deve ser passado em minutos absolutos (ex: `15 * epoch`). O modelo `.mod` divide internamente esse valor pelo horizonte total (ex: 1440 min) para normalizar entre 0 e 1, espelhando a lógica do `features.py`.
2.  **Cálculo de Urgência:** O parâmetro `UrgencyScore` deve ser pré-calculado como $1 / \max(\text{prazo} - \text{agora}, 0.1)$.
3.  **GridLimit:** O modelo está configurado com um limite de rede (`GridLimit`) padrão alto ($10^9$), replicando o comportamento do `solver.py` que foca nas restrições individuais dos carregadores. Pode ser ajustado em `dados.dat` para testes de estresse da rede.

## 📊 Interpretando a Solução (`solution.sol`)

Ao analisar o arquivo de saída para a instância de exemplo incluída:

  * **Função Objetivo:** Se o valor for negativo (ex: `-25.34`), isso é esperado e correto. Como os pesos `Zeta` aprendidos podem ser negativos (para indicar benefício ou urgência), a soma ponderada do "Valor Futuro" frequentemente resulta em um valor negativo, servindo como um "score" para rankear as decisões.
  * **Variáveis X (Conexão):**
      * `X[1,0,101] = 1`: O veículo 101 foi alocado ao Carregador 1.
      * Valores `0` indicam que o veículo foi deixado em espera (fila), uma decisão estratégica tomada pelo ADP baseada no preço ou na urgência.
  * **Variáveis Q (Energia):**
      * Se `Q` for 0 mesmo com `X=1`, significa que o veículo está conectado mas o sistema decidiu não carregar agora (esperando preço baixar), uma manobra clássica de *Smart Charging*.
