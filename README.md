# TDE — Rede Neural aplicada a acidentes em rodovias federais

Trabalho Discente Efetivo da disciplina de Redes Neurais: uma **MLP implementada
do zero em NumPy** (sem frameworks de aprendizado) para estimar a gravidade de
acidentes registrados pela Polícia Rodoviária Federal em 2024, com API FastAPI,
interface Next.js e PostgreSQL.

**Integrantes:** Felipe Medeiros Castello Branco · Herbeth Lucas de Sousa Pereira ·
Samuel Pereira da Silva Varão
**Professor:** Edilson Carlos Silva Lima
**Curso / instituição / semestre:** `[CURSO]` · `[INSTITUIÇÃO]` · `[SEMESTRE]`

> Protótipo acadêmico. Não é ferramenta de decisão em segurança viária.

## Status

| Fase | Entrega | Situação |
|---|---|---|
| 0 | Fundação, dataset e validação | ✅ concluída |
| 1 | Pipeline de dados (`backend/nn/data.py`) | ✅ concluída |
| 2 | Rede neural (`backend/nn/model.py`) | ✅ concluída |
| 3 | Métricas e exportação | ✅ concluída |
| 4 | Notebook do TDE | ✅ concluída |
| 5 | API FastAPI + PostgreSQL | ✅ concluída |
| 6 | Frontend Next.js | ✅ concluída |
| 7 | Docker Compose (raiz) | ✅ concluída |
| 8 | Documento, ensaio e entrega | 🚧 entregáveis prontos; pendências humanas |

Detalhes em [`.specs/backend.md`](.specs/backend.md),
[`.specs/frontend.md`](.specs/frontend.md) e controle em
[`.specs/checklist.md`](.specs/checklist.md). A pasta `.specs/` é local e não
versionada.

## Dataset

DATATRAN 2024 da PRF — 73.202 ocorrências, 30 colunas, alvo desbalanceado
(7,1% com vítima fatal). Fonte, dicionário completo, hashes e limitações em
[`docs/dataset.md`](docs/dataset.md).

```bash
make fetch        # baixa e valida o CSV em backend/data/raw/datatran2024.csv
make data-check   # apenas valida o arquivo local
```

## Estrutura

O repositório separa o backend Python do frontend Next.js. Arquivos de
orquestração e documentação compartilhada ficam na raiz.

```
backend/                 API e núcleo de rede neural (Python)
├── nn/                  modelo, dados, métricas e exportação (NumPy)
├── api/                 FastAPI + Dockerfile: treino, SSE e simulador
├── scripts/             download/validação e seed de demonstração
├── tests/               testes unitários e de integração
├── notebooks/           notebook do TDE
├── data/raw/            CSV baixado (não versionado)
├── artifacts/           runs, pesos e curvas (não versionado)
└── pyproject.toml       dependências e configuração de testes/lint/mypy

frontend/                Next.js + Dockerfile (standalone)

docs/                    dicionário do dataset e documento explicativo
.specs/                  especificação, checklist e materiais de apoio (local)

README.md
Makefile
.gitignore
docker-compose.yml       db + api + web
```

## Subindo com Docker

Requisitos: Docker 29+ e Docker Compose v2+.

```bash
cp .env.example .env   # opcional: ajuste portas/credenciais
make up                # sobe data + db + api + web em background (build incluso)
```

O serviço one-shot `data` baixa e valida o CSV automaticamente em
`backend/data/raw/` caso ele ainda não exista. Se preferir baixar antes:
`make fetch`.

Depois de subir:

| Serviço | URL |
|---|---|
| Interface | http://localhost:3000 |
| API / OpenAPI | http://localhost:8000/api/docs |
| Healthcheck | http://localhost:8000/api/health |

Para popular a apresentação com um treino pronto:

```bash
make seed    # cria o run "Demo — PRF 2024" no Postgres e em backend/artifacts/
```

Operação:

```bash
make ps           # estado dos serviços
make logs         # logs em tempo real
make down         # derruba containers (preserva pgdata e artefatos)
make reset-db     # apaga containers + volume pgdata (destrutivo)
make db-shell     # psql dentro do container
```

A ordem de inicialização é garantida por dependências e healthchecks:
`data` (CSV) → `db` (Postgres 16) → `api` (FastAPI) → `web` (Next.js standalone).

### Arquitetura dos containers

```
Navegador :3000
   │
   ▼
web (Next.js standalone)
   │  API_INTERNAL_URL=http://api:8000 (proxy runtime + SSE)
   ▼
api (FastAPI + Uvicorn) :8000
   │  DATABASE_URL=postgresql+psycopg://...@db:5432/tde
   ├── volume ./backend/data:/app/data
   ├── volume ./backend/artifacts:/app/artifacts
   ▼
db (postgres:16-alpine) + volume nomeado pgdata
```

O serviço `data` (python:3.12-slim) executa `scripts/fetch_data.py` uma vez;
ele é idempotente e não sobe se o CSV já estiver íntegro.

## Ambiente local (sem Docker)

Requisitos: Python 3.12+ e Node 24+.

```bash
make venv         # cria .venv na raiz
make install      # instala o backend + dependências de desenvolvimento
make test         # pytest do backend
make lint         # ruff
make typecheck    # mypy em nn e api
make types        # OpenAPI + tipos TypeScript
cd frontend && npm install && npm run dev
```

## Troubleshooting

**`dependency db failed to start` / container sem rede ou sem portas** — quase sempre é
resíduo de um `up` interrompido. Recrie a stack preservando os dados:

```bash
make refresh
```

Se persistir, veja o erro real do banco:

```bash
docker compose ps -a
docker compose logs db --tail=80
docker compose down --remove-orphans
make up
```

**Porta 5432 ocupada** — outro Postgres local está rodando. Altere no `.env`:

```env
DB_PORT=55432
```

**“This page couldn’t load” ao clicar em uma rota** — normalmente o `web` estava
reiniciando (build, `make refresh` ou `Ctrl+C` no `make up` antigo). Confira:

```bash
docker compose ps
curl -I http://localhost:3000/treinar
```

Se `web` estiver `healthy`, basta recarregar com `Ctrl+Shift+R`. O alvo `make up`
agora sobe em background; use `make logs` para acompanhar sem derrubar a stack.

**A API não fica saudável** — confira `make logs` e se o CSV existe em
`backend/data/raw/datatran2024.csv`. O serviço `data` baixa automaticamente.

**Quero começar do zero** — `make reset-db` remove o volume `pgdata`; os
artefatos em `backend/artifacts/` continuam no host. Para apagar também:

```bash
rm -rf backend/artifacts/runs
```

**Mudei dependências** — `make build` reconstrói as imagens; `make up` já faz
build quando necessário.

## Entregáveis

| Arquivo | Conteúdo |
|---|---|
| `backend/notebooks/TDE_rede_neural_acidentes_PRF.ipynb` | Notebook completo, executado com saídas |
| `docs/TDE_documento_explicativo.docx` / `.pdf` | Documento nas 8 seções do guia |
| `docs/TDE_apresentacao.pptx` | 12 slides com notas e roteiro de 10 min |
| `docs/screenshots/` | Dashboard, treino, resultados, comparação, dados e simulador |
| `docs/roteiro_demo.md` | Roteiro da demo + plano B com `make seed` |
| `docs/backup_run/` | Artefatos do run principal (model, weights, curvas, métricas) |
| `docs/PENDENCIAS_ENTREGA.md` | Itens humanos/externos a preencher |
| `dist/TDE_redes_neurais_entrega.zip` | Pacote final (gerado por `make package`) |

```bash
make deliverables   # DOCX, PDF, slides, QR, roteiro e backup
make screenshots    # requer a stack no ar
make package        # zip final em dist/
```

> A entrega depende de preencher `[CURSO]`, `[INSTITUIÇÃO]` e `[SEMESTRE]` e confirmar
> com o professor a autorização do grupo de 3 integrantes.

## Roadmap

1. Pipeline de dados com split estratificado 60/20/20 e preprocessor serializável.
2. `NnModel` com forward/loss/backprop, otimizadores e early stopping.
3. Notebook com EDA, treino, avaliação e análise crítica.
4. API com fila de treino, SSE e persistência em PostgreSQL.
5. Interface com formulário completo, gráficos e simulador.
6. `docker compose up --build` sobe banco, API e front. ✅
