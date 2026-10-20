# Guia do Projeto — Preditor de Falha e Risco em Dispositivos de Rede

Projeto multidisciplinar (Estrutura de Dados II, Redes de Computadores e Análise e Projeto de Sistemas).  
Repositório: https://github.com/ViniEduOliveira/project-redes

> Este guia explica **para que o projeto serve, o que precisa para rodar, como usar e o que ele devolve**.  
> Ele foi escrito a partir do `README.md`, do `Memorando_de_Decisao_grupo4.md` e do `coleta.py`. Onde algo não pôde ser confirmado no código, aparece a marca **(conferir)**.

---

## 1. O que é o projeto

Uma aplicação que **mede a qualidade de enlaces de rede** e usa uma **árvore de decisão** (aprendizado de máquina) para classificar o estado de cada conexão em:

| Classe | Significado para quem opera a rede |
|---|---|
| **OK** | Comportamento normal. Não agir. |
| **RISCO** | Começou a piorar. Observar. |
| **FALHA** | Degradação forte. Investigar. |

O ponto central é que a classificação compara cada conexão com o **seu próprio normal**, e não com um valor fixo. Um enlace Brasil → Japão sempre terá RTT alto, e isso **não** é falha. Falha é o enlace ficar muito pior do que ele costuma ser.

## 2. Por que ele é útil

- **Evita alarme falso.** Um limite global como "RTT acima de 100 ms = problema" dispara para todo caminho longo e deixa passar problemas em caminhos curtos. Comparar cada fluxo com o próprio histórico resolve isso.
- **Detecta antes de quebrar.** Jitter subindo e perda de pacotes aparecendo costumam vir antes de uma queda total. O projeto também busca prever o estado alguns minutos à frente (o diário fala em 12 minutos).
- **Independe da rota.** País, IP e nome da rota não entram como variável da árvore, então o modelo não aprende "rota X é ruim", e sim "este comportamento é anormal".
- **Usa dados reais e públicos.** As medições vêm do RIPE Atlas, uma rede mundial de sondas. Não é preciso montar infraestrutura nem gastar crédito.
- **É interpretável.** Uma árvore de decisão mostra as regras que levaram a cada decisão, então dá para explicar por que um fluxo foi marcado como RISCO ou FALHA.

## 3. Conceitos rápidos

| Termo | O que é |
|---|---|
| **RTT / delay / latência** | Tempo de ida e volta de um pacote ping, em milissegundos. |
| **Jitter** | Variação do RTT entre os pacotes de uma mesma rajada. Calculado como desvio-padrão dos RTTs, só se houver 2 ou mais respostas. |
| **Perda (%)** | `(enviados − recebidos) / enviados × 100`. |
| **Timeout** | Rajada sem nenhuma resposta. Fica no arquivo e **nunca** é transformado em RTT 0. |
| **Fluxo** | Um par origem → destino: `probe_id \| dst_addr`. É a unidade de análise. |
| **Probe / sonda** | Dispositivo do RIPE Atlas que dispara o ping (a origem). |
| **Anchor** | Sonda mais robusta do RIPE Atlas, usada aqui como destino. |
| **Baseline** | O "normal" de cada fluxo, calculado num período de referência (Período A). |
| **Período A / B** | A serve para o baseline. B é o que será rotulado. Os dois não podem se sobrepor. |

## 4. Requisitos mínimos

### Para rodar a coleta (`coleta.py`)

| Item | Requisito |
|---|---|
| Internet | Conexão ativa com acesso a `atlas.ripe.net` |
| Python | 3.9 ou superior (recomendado) |
| Bibliotecas | `requests`, `pandas` |
| Conta/chave RIPE | **Não precisa.** O script só faz `GET` em dados públicos |
| Créditos RIPE | **Não gasta.** Nenhuma medição nova é criada |
| Espaço em disco | Pequeno (o resultado é um CSV) |
| Ambiente | Google Colab (com Google Drive) **ou** computador local |

### Para os notebooks de baseline, rotulagem e árvore

| Item | Requisito |
|---|---|
| Python / Jupyter | Python 3.9+ e Jupyter, Google Colab (**Recomendado** utilizado durante a produção do projeto) ou Visual Studio Code |
| Bibliotecas | `pandas`, `numpy`, `scikit-learn`, `matplotlib` **(conferir se é isso mesmo)** |
| Entrada | O `medicoes_consolidadas.csv` gerado pela coleta |

> **Sugestão:** criar um `requirements.txt` na raiz do repositório:
> ```
> requests
> pandas
> numpy
> scikit-learn
> matplotlib
> ```

## 5. Tutorial: como rodar

### Opção A — Google Colab (mais fácil, é como o grupo usa)

1. Acesse https://colab.research.google.com e entre com sua conta Google.
2. Abra o notebook `2_Coleta_de_dados.ipynb`: **Arquivo → Abrir notebook → GitHub** e cole `ViniEduOliveira/project-redes`. Ou envie o arquivo por **Upload**.
3. Execute as células em ordem (**Ctrl+Enter** em cada uma, ou **Ambiente de execução → Executar tudo**).
4. Quando o Colab pedir, **autorize o acesso ao Google Drive**. O script usa isso para salvar o resultado.
5. Aguarde. O script mostra no console cada dupla de medições encontrada.
6. No final, o arquivo estará em `Meu Drive/ripe_atlas/raw/medicoes_consolidadas.csv`.

### Opção B — No seu computador

```bash
# 1. Baixar o projeto
git clone https://github.com/ViniEduOliveira/project-redes
cd project-redes

# 2. (Recomendado) criar ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Instalar dependências
pip install requests pandas

# 4. Rodar a coleta
python coleta.py
```

Fora do Colab, o script cria sozinho a pasta `./ripe_atlas/raw/` e salva lá o CSV.

### Ordem de uso das etapas do projeto

```
Coleta (coleta.py / notebook 2)
        │  gera medicoes_consolidadas.csv
        ▼
Baseline e Rotulagem (notebook da Tarefa 2)
        │  calcula o "normal" de cada fluxo e atribui OK / RISCO / FALHA
        ▼
Árvore de decisão (notebook da Tarefa 3)
           treina o modelo (o histórico de commits cita divisão 70% treino, 15% teste e validação)
```

## 6. Como a coleta funciona (por dentro)

1. **Mapeia as Anchors ativas** do RIPE Atlas (`/api/v2/anchors/`), guardando endereço, cidade e país.
2. **Embaralha os destinos** com semente fixa (`random.seed(42)`) e, para cada um, procura medições públicas de ping IPv4 em andamento.
3. **Forma uma "dupla"**: duas medições diferentes do mesmo destino. Em cada uma sorteia 5 probes de origem, sem repetir probe entre duplas.
4. **Baixa os resultados** de cada medição na janela de tempo configurada.
5. **Consolida** tudo em uma tabela e grava `medicoes_consolidadas.csv`.

Parâmetros no topo do `coleta.py`:

| Parâmetro | Valor atual | O que controla |
|---|---|---|
| `TOTAL_DUPLAS` | 15 | Quantos destinos/duplas coletar |
| `PROBES_POR_MEDICAO` | 5 | Origens por medição |
| `HORAS_COLETA` | 366 | Tamanho da janela de tempo (≈ 15 dias, terminando agora) |
| `TIMEOUT_S` | 60 | Tempo máximo de espera por requisição HTTP |
| `FORMATO_TABELAR` | `csv` | Formato do arquivo de saída |

Tamanho máximo teórico: 15 duplas × 2 medições × 5 probes = **150 fluxos**.

## 7. O que o programa devolve

### Arquivo de saída

`ripe_atlas/raw/medicoes_consolidadas.csv`: uma linha por medição ICMP (uma rajada de pings) de um fluxo, com timestamp.

### Colunas

**Vindas do RIPE Atlas** (os nomes exatos dependem da resposta da API **(conferir abrindo o CSV)**):

| Coluna | O que é |
|---|---|
| `timestamp` | Momento da medição (Unix, UTC) |
| `prb_id` | ID da sonda de origem |
| `msm_id` | ID da medição |
| `dst_addr` / `dst_name` | Destino |
| `avg`, `min`, `max` | RTT médio, mínimo e máximo da rajada (ms) |
| `sent`, `rcvd` | Pacotes enviados e recebidos |
| `result` | Lista com o RTT de cada pacote da rajada (guardada como texto) |

**Adicionadas pelo script:**

| Coluna | O que é |
|---|---|
| `id_medicao` | ID da medição de onde veio a linha |
| `medicao_parceira` | ID da outra medição da dupla |
| `destino_alvo` | Nome (FQDN) da Anchor de destino |
| `cidade_alvo` | Cidade e país do destino (só para auditar diversidade) |
| `papel_dupla` | "Medição A" ou "Medição B" dentro da dupla |

> **Atenção:** "Medição A/B" (`papel_dupla`) **não é** o mesmo que Período A/B. A primeira diz qual das duas medições da dupla; o segundo são dois blocos de tempo.

### Cuidados com os dados

- Na API do RIPE Atlas, `avg = -1` significa que **não houve resposta**. Isso deve virar **vazio**, nunca 0.
- No CSV, `result` é salvo como texto. Para usar, é preciso converter de volta para lista.
- O programa **não calcula** perda, jitter nem `fluxo_id`. Isso é feito depois, a partir das colunas brutas.

### Exemplo: calcular delay, perda, jitter e timeout

```python
import ast
import numpy as np
import pandas as pd

df = pd.read_csv("ripe_atlas/raw/medicoes_consolidadas.csv")

def rtts(texto):
    try:
        lista = ast.literal_eval(texto)
    except Exception:
        return []
    return [p["rtt"] for p in lista if isinstance(p, dict) and "rtt" in p]

df["fluxo_id"]   = df["prb_id"].astype(str) + "|" + df["dst_addr"].astype(str)
df["rtt_ms"]     = df["avg"].where(df["avg"] > 0)            # -1 vira vazio
df["perda_pct"]  = (df["sent"] - df["rcvd"]) / df["sent"] * 100
df["jitter_ms"]  = df["result"].apply(rtts).apply(
    lambda r: float(np.std(r, ddof=1)) if len(r) >= 2 else np.nan
)
df["timeout_atual"] = (df["rtt_ms"].isna() | (df["perda_pct"] == 100)).astype(int)

print(df[["fluxo_id", "rtt_ms", "perda_pct", "jitter_ms", "timeout_atual"]].head())
```

### Relatório rápido de qualidade (sem classificar nada)

```python
print("Registros:", len(df))
print("Fluxos:", df["fluxo_id"].nunique())
print("Timeouts:", df["timeout_atual"].sum())
print("Duplicatas:", df.duplicated(subset=["fluxo_id", "timestamp"]).sum())
print(df.groupby("fluxo_id")["timestamp"].agg(["count", "min", "max"]).head())
print(df[["rtt_ms", "perda_pct"]].describe().loc[["min", "50%", "max"]])
```

## 8. Pontos de atenção conhecidos

Estes pontos ajudam a evitar surpresas e a melhorar o projeto:

| Ponto | Por quê importa | Sugestão |
|---|---|---|
| A janela é relativa a "agora" (`now − 366 h`) | Cada execução pega um período diferente; o recorte de referência (06/09/2026 04:32 UTC, 7 + 7 dias) não é reproduzido | Fixar datas de início e fim em um arquivo de configuração |
| Parâmetros dentro do código | Difícil alterar sem mexer no script | Mover para `config/` |
| `except: continue` sem registro | Erros de rede somem sem aviso | Registrar o erro e tentar de novo (retry) |
| Só o CSV é salvo | O JSON original da API se perde | Salvar também o JSON bruto em `data/raw/` |
| Rodar de novo sobrescreve o CSV | Não há controle de duplicatas | Gravar por medição e pular o que já existe |
| Sem `requirements.txt` | Quem clona não sabe o que instalar | Adicionar o arquivo (modelo na seção 4) |
| Resultado depende da disponibilidade da API | O RIPE Atlas pode estar lento ou fora do ar | Aumentar `TIMEOUT_S` e tentar mais tarde |

## 9. Problemas comuns

| Sintoma | Provável causa | O que fazer |
|---|---|---|
| `Erro: Nenhum dado retornado.` | Janela sem dados, API fora do ar ou nenhuma dupla válida | Rodar de novo mais tarde; conferir a internet |
| `Total de duplas consolidadas: X de 15` com X pequeno | Poucos destinos com 2 medições públicas e probes livres suficientes | Reduzir `PROBES_POR_MEDICAO` ou aumentar a lista de alvos |
| `ModuleNotFoundError: requests` | Dependência não instalada | `pip install requests pandas` |
| Colab pede permissão do Drive | Comportamento normal | Autorizar com a conta do grupo |
| Muita demora | Muitas requisições em sequência | É esperado; aguardar o fim da execução |
| `ModuleNotFoundError: google.colab` | Rodando fora do Colab | Não é erro; o script cai no caminho local `./ripe_atlas/raw` |

## 10. Sobre o dashboard

O `README.md` descreve como objetivo um **dashboard em tempo real** que monitora IPs por ping, classifica cada dispositivo em OK, RISCO ou FALHA e permite **injetar eventos simulados** para testar a reação da rede. **(conferir: não encontrei o código do dashboard no repositório; as etapas visíveis são coleta, baseline/rotulagem e árvore.)**

## 11. Equipe

Vinicius Eduardo Santos de Oliveira, Giulia Ayumi Shimada Cardoso, Heitor Estrela de Andrade, Gabriel Romão da Silva e Miguel Augusto da Costa Souza.

## 12. Referências

- RIPE Atlas, manual da API REST: https://atlas.ripe.net/docs/apis/rest-api-manual/
- RIPE Atlas, créditos: https://atlas.ripe.net/docs/getting-started/credits
- RIPE Atlas, limite de requisições: https://atlas.ripe.net/docs/apis/rest-api-manual/core-concepts/rate-limiting/
- Memorando de Decisão do grupo (escolha do RIPE Atlas em vez do dataset CAIDA Ark): `Memorando_de_Decisao_grupo4.md`
