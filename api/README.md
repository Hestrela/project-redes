# API de previsao t+12

API experimental que recebe rajadas de ping normalizadas a partir dos resultados do RIPE Atlas, calcula as oito features do experimento preditivo e consulta o modelo XGBoost t+12.

## Contrato

`POST /api/v1/previsoes/t12` recebe:

- `fluxo_id`: identificador estavel do fluxo.
- `calibracao`: medições do periodo inicial usado como baseline; precisa conter pelo menos 1.500 medições com RTT valido.
- `medicoes_recentes`: de uma a cinco medições posteriores a calibracao. A ultima e usada para gerar a previsao; as anteriores alimentam as janelas moveis.

Cada medição representa uma rajada de ping. `rtts_ms` contem os RTTs das respostas recebidas; `enviados` informa quantos pacotes foram enviados. Uma lista vazia de RTTs representa uma rajada sem resposta, nunca RTT igual a zero.

Exemplo estrutural de entrada (a requisicao real deve incluir o minimo de 1.500 registros validos em `calibracao`):

```json
{
  "fluxo_id": "probe-123|203.0.113.10",
  "calibracao": [
    {
      "timestamp_utc": "2026-10-01T00:00:00Z",
      "enviados": 4,
      "rtts_ms": [21.2, 20.9, 21.5, 21.1]
    }
  ],
  "medicoes_recentes": [
    {
      "timestamp_utc": "2026-10-15T12:00:00Z",
      "enviados": 4,
      "rtts_ms": [22.0, 21.7, 22.3, 21.9]
    }
  ]
}
```

A resposta inclui `classe_prevista` (`OK`, `RISCO` ou `FALHA`), horizonte e horario previstos, probabilidades, features calculadas e SHA-256 do artefato.

## Execucao local

Na raiz do repositorio:

```bash
python -m pip install -r requirements.txt
uvicorn api.main:app --reload
```

Documentacao interativa: <http://127.0.0.1:8000/docs>.

O artefato esperado e `predicao_12min/modelos/xgboost_t12.joblib`. As versoes das bibliotecas de inferencia devem ser alinhadas as versoes usadas para treinar e serializar esse artefato antes de publicar a API.

## Prever diretamente por Measurement ID

`POST /api/v1/previsoes/ripe-atlas` consulta os resultados publicos do RIPE Atlas usando somente `GET`. Nao e necessario fornecer chave de API. Sem datas informadas, consulta os ultimos 14 dias. Tambem e possivel informar `inicio_utc` e `fim_utc`; a janela maxima e 14 dias.

```json
{
  "measurement_id": 109069241,
  "probe_id": 1001323,
  "inicio_utc": "2026-10-01T00:00:00Z",
  "fim_utc": "2026-10-15T00:00:00Z"
}
```

`probe_id`, `inicio_utc` e `fim_utc` sao opcionais. Sem `probe_id`, a API retorna uma previsao por fluxo (`probe_id|dst_addr`) que tenha dados suficientes; os demais fluxos aparecem em `fluxos_ignorados`. Para cada fluxo, a primeira semana da janela consultada e usada como calibracao, seguindo o notebook do projeto, e as cinco medicoes mais recentes posteriores alimentam as janelas do modelo. Sao necessarias pelo menos 1.500 medicoes com RTT valido na calibracao.

O RIPE Atlas aceita menos de sete dias por requisicao; por isso a API divide a janela de ate 14 dias em blocos de seis dias. Quando `probe_id` e informado, ele tambem e enviado ao RIPE para reduzir o volume. Para uso frequente, uma versao de producao deve persistir os resultados/baselines e evitar baixar repetidamente o mesmo intervalo.

## Deploy na Vercel

O repositorio esta configurado para deploy como Vercel Function (Python/FastAPI). Os arquivos relevantes na raiz sao:

| Arquivo | Funcao |
|---|---|
| `vercel.json` | Rewrites, includeFiles/excludeFiles, maxDuration |
| `requirements.txt` | Dependencias Python (lido automaticamente pela Vercel) |
| `.python-version` | Fixa Python 3.13 (compativel com o artefato do modelo) |
| `.vercelignore` | Impede upload de `metadados/` (~303 MB) e outros nao-runtime |

### Passos no painel da Vercel

1. Importe o repositorio no painel (Import Git Repository).
2. Em **Settings → General → Root Directory**, mantenha a raiz (`./`).
3. Em **Settings → Git → Production Branch**, selecione a branch `API`.
4. O framework sera detectado automaticamente como "Other" ou "Python"; nao precisa ajustar.
5. Faca deploy; a Vercel instalara as dependencias do `requirements.txt` e usara Python 3.13.

### Endpoints disponiveis apos deploy

- `GET /api/v1/saude` — health check
- `GET /api/v1/modelo` — informacoes do modelo
- `POST /api/v1/previsoes/t12` — previsao com dados fornecidos pelo cliente
- `POST /api/v1/previsoes/ripe-atlas` — previsao consultando o RIPE Atlas
- `GET /docs` — documentacao interativa (Swagger UI)

### maxDuration

A Function esta configurada com `maxDuration: 300` (5 minutos), que e o limite do plano Hobby. A rota `/ripe-atlas` faz ate 3 requisicoes sequenciais ao RIPE Atlas (janela de 14 dias em blocos de 6 dias). Se o plano for Pro ou Enterprise, considere aumentar para 60–120 segundos para conforto, ou manter 300 para o pior caso. Valores acima de 300 exigem Pro.

### Seguranca (recomendacoes)

A API esta atualmente **sem autenticacao**. Isso funciona para demonstracao, mas para producao recomenda-se:

1. **Rate limiting** — habilitar no painel da Vercel: **Settings → Security → Rate Limiting**. Sugestao: 60 req/min por IP nos endpoints POST.
2. **Autenticacao por API Key** — se necessario, adicionar uma variavel de ambiente `API_KEY` no painel (**Settings → Environment Variables**) e validar no header `Authorization: Bearer <key>` usando um middleware FastAPI. Isso nao foi implementado para nao quebrar o uso existente sem autenticacao.
3. **CORS** — por padrao o FastAPI nao adiciona headers CORS. Se um frontend em outro dominio precisar acessar a API, adicionar `CORSMiddleware` com as origens permitidas.

### Versoes das bibliotecas e o modelo

O modelo `xgboost_t12.joblib` foi serializado com `joblib` (pickle) em Python 3.13. As versoes exatas de `xgboost` e `scikit-learn` usadas no treinamento **nao estao registradas**. O ambiente local valida o modelo com xgboost 3.4.1 e scikit-learn 1.9.1. Se o deploy falhar ao carregar o modelo, ajuste as versoes no `requirements.txt` para coincidir com as do notebook de treinamento (`predicao_12min/experimento_preditivo_12min.ipynb`).

## Limites deste esqueleto

- A API e stateless: no endpoint `/t12`, o cliente precisa reenviar a calibracao em cada chamada. No endpoint `/ripe-atlas`, os resultados e a calibracao sao consultados novamente a cada chamada; uma proxima etapa pode persistir baselines por fluxo.
- As probabilidades sao as saidas do classificador, nao uma garantia de confianca calibrada.
- A API nao guarda historico de previsoes nem faz coleta automatica no RIPE Atlas.