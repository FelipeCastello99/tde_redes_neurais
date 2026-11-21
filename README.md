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
| 1 | Pipeline de dados (`nn/data.py`) | ✅ concluída |
| 2 | Rede neural (`nn/model.py`) | ⏳ próxima |
| 3 | Métricas e exportação | ⏳ |
| 4 | Notebook do TDE | ⏳ |
| 5 | API FastAPI + PostgreSQL | ⏳ |
| 6 | Frontend Next.js | ⏳ |
| 7 | Docker Compose (raiz) | ⏳ |
| 8 | Documento, ensaio e entrega | ⏳ |

Detalhes em [`.spec/backend.md`](.spec/backend.md), [`.spec/frontend.md`](.spec/frontend.md)
e controle em [`.spec/checklist.md`](.spec/checklist.md).

## Dataset

DATATRAN 2024 da PRF — 73.202 ocorrências, 30 colunas, alvo desbalanceado
(7,1% com vítima fatal). Fonte, dicionário completo, hashes e limitações em
[`docs/dataset.md`](docs/dataset.md).

```bash
make fetch        # baixa e valida o CSV (data/raw/datatran2024.csv)
make data-check   # apenas valida o arquivo local
```

## Estrutura

```
nn/            núcleo NumPy (modelo, dados, métricas, exportação)
api/           FastAPI (treino, histórico, SSE, simulador)
web/           Next.js (a partir da Fase 6)
notebooks/     notebook do TDE
scripts/       download/validação e seed de demonstração
docs/          documentação e documento explicativo
tests/         testes unitários e de integração
data/raw/      CSV baixado (não versionado)
artifacts/     runs, pesos e curvas (não versionado)
```

## Ambiente

Requisitos: Python 3.12+, Docker 29+ e Docker Compose v2+.

```bash
make venv         # cria .venv
make install      # instala o projeto + dependências de desenvolvimento
```

## Roadmap

1. Pipeline de dados com split estratificado 60/20/20 e preprocessor serializável.
2. `NnModel` com forward/loss/backprop, otimizadores e early stopping.
3. Notebook com EDA, treino, avaliação e análise crítica.
4. API com fila de treino, SSE e persistência em PostgreSQL.
5. Interface com formulário completo, gráficos e simulador.
6. `docker compose up --build` sobe banco, API e front.
