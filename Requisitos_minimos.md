# Especificação de Requisitos Mínimos (Projeto Preditivo de Redes t + 12 min)

## 1. Requisitos Funcionais (RF)

| ID | Descrição do Requisito |
| :--- | :--- |
| **RF01** | **Ingestão de Telemetria de Rede:** O sistema deve consumir e armazenar dados públicos de telemetria (RTT, perda de pacotes e jitter) da API do RIPE Atlas na camada bruta (`/metadados/medicoes/`). |
| **RF02** | **Tratamento e Normalização:** O pipeline deve limpar, tratar nulos/timeouts e normalizar timestamps, registando os dados tratados na camada intermédia (`/metadados/etapa 2/`). |
| **RF03** | **Engenharia de 8 Atributos:** O sistema deve extrair o vetor $X$ de 8 atributos estatísticos no instante $t$ (`z_robusto`, `aumento_pct`, `jitter_relativo`, `perda_pct`, `timeout_atual`, `n5_timeout`, `n5_aumento80`, `n5_risco`) e gerar o dataset final (`/metadados/preditivo/dataset_preditivo_t12_v1.csv`). |
| **RF04** | **Particionamento Temporal Cego:** O módulo de preparação de dados deve particionar o dataset de forma estritamente cronológica (70% Treino, 15% Validação, 15% Teste Cego), impedindo o vazamento de informação do futuro (*data leakage*). |
| **RF05** | **Treinamento e Comparação de Modelos:** O pipeline deve treinar e comparar os algoritmos Árvore de Decisão (CART), Random Forest e XGBoost, calculando métricas de Acurácia, F1-Macro e Precisão/Recall por classe (`OK`, `RISCO`, `FALHA`). |
| **RF06** | **Serialização e Persistência do Modelo:** O sistema deve exportar o modelo campeão otimizado em formato `.joblib` para a pasta `/predicao_12min/modelos/`. |
| **RF07** | **Pipeline Executável de Inferência:** O sistema deve disponibilizar notebooks/scripts funcionais em `/predicao_12min/` capazes de recarregar o ficheiro `.joblib` e realizar a classificação preditiva de novas amostras no horizonte $t + 12\text{ min}$. |
| **RF08** | **Apresentação e Visualização (Artigo Web):** O projeto deve fornecer uma interface web responsiva em `/artigo/` (`index.html`, `style.css`, `script.js`) para exibição da metodologia, arquitetura de dados e quadros comparativos. |
| **RF09** | **Validação e Sanitização de Dados:** O pipeline deve validar o esquema de colunas do dataset, garantindo o tratamento adequado de valores nulos ou ausentes antes do treino e inferência. |
| **RF10** | **Registo de Resultados e Métricas:** O sistema deve exportar relatórios de avaliação e matrizes de confusão detalhadas na pasta `/predicao_12min/resultados/`. |

---

## 2. Requisitos Não-Funcionais (RNF)

| ID | Categoria | Descrição do Requisito |
| :--- | :--- | :--- |
| **RNF01** | Desempenho | **Baixa Latência de Inferência:** O modelo otimizado `.joblib` deve realizar a inferência de cada amostra em tempo inferior a **2 ms**. |
| **RNF02** | Confiabilidade | **Alta Precisão na Classe Crítica:** O modelo campeão (XGBoost) deve manter uma precisão superior a **90% na classe FALHA** no conjunto cego de teste, minimizando alarmes falsos. |
| **RNF03** | Eficiência | **Eficiência de Treinamento:** O tempo de execução do pipeline completo de treino do XGBoost não deve ultrapassar **10 segundos** em ambiente padrão (Google Colab ou local). |
| **RNF04** | Precisão Temporal | **Horizonte de Projeção:** O modelo deve prever o estado operacional da rede estritamente para o horizonte de 12 minutos no futuro ($t + 12\text{ min}$) com margem aceitável de tolerância de **$\pm 30$ segundos**. |
| **RNF05** | Portabilidade | **Compatibilidade do Ambiente:** O pipeline deve ser desenvolvido em Python 3.10+ utilizando bibliotecas padrão de mercado (`scikit-learn`, `xgboost`, `joblib`, `pandas`). |
| **RNF06** | Usabilidade | **Acessibilidade Web:** A interface gráfica em `/artigo/` deve ser compatível com os principais navegadores (Chrome, Firefox, Edge, Safari) e adaptar-se a ecrãs móveis e desktop. |
| **RNF07** | Reprodutibilidade | **Determinismo de Experimentos:** Todos os scripts de treino e divisão de dados devem utilizar semente aleatória fixa (`random_state=SEED`) para garantir resultados auditáveis. |
| **RNF08** | MLOps / Versionamento | **Rastreabilidade de Artefatos:** Os ficheiros do modelo gerados em `/predicao_12min/modelos/` devem manter o versionamento atrelado ao dataset correspondente. |

---

## 3. Regras de Negócio (RN)

| ID | Nome | Descrição |
| :--- | :--- | :--- |
| **RN01** | **Independência da Camada de Apresentação** | O pipeline de Inteligência Artificial e a inferência preditiva devem funcionar autonomamente em ambiente de script/notebook, sem dependência direta da interface web. |
| **RN02** | **Isolamento de Atributos Futuros** | É estritamente proibido utilizar qualquer medição recolhida após o instante $t$ para prever a classe do estado em $t + 12\text{ min}$. |
| **RN03** | **Priorização Contra Alarmes Falsos** | Em cenários de ajuste de limiar (*trade-off*), a precisão da classe `FALHA` deve ter prioridade sobre a taxa de cobertura (*recall*), garantindo confiabilidade aos operadores de rede. |