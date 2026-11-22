SHELL := /bin/bash
PY ?= python3
VENV := .venv
BACKEND := backend
COMPOSE ?= docker compose

.DEFAULT_GOAL := help

.PHONY: help fetch data-check venv install test lint typecheck types up down refresh build logs ps db-shell reset-db seed detailed-doc detailed-pdf deliverables screenshots package clean clean-pyc

help:
	@echo "TDE Redes Neurais — alvos disponíveis:"
	@echo "  make fetch       Baixa e valida o CSV do DATATRAN 2024"
	@echo "  make data-check  Valida apenas o CSV local"
	@echo "  make venv        Cria o ambiente virtual .venv na raiz"
	@echo "  make install     Instala o backend e as dependências de desenvolvimento"
	@echo "  make test        Roda o pytest do backend"
	@echo "  make lint        Roda o ruff no backend"
	@echo "  make typecheck   Roda o mypy no núcleo e na API"
	@echo "  make types       Gera openapi.json e os tipos TypeScript do frontend"
	@echo "  make up          Sobe db + api + web em background (build incluso)"
	@echo "  make down        Derruba os containers"
	@echo "  make refresh     Recria tudo do zero preservando pgdata/artifacts"
	@echo "  make build       Reconstrói as imagens"
	@echo "  make logs        Acompanha os logs dos serviços"
	@echo "  make ps          Mostra o estado dos serviços"
	@echo "  make db-shell    Abre o psql no container do Postgres"
	@echo "  make reset-db    Remove containers e o volume pgdata"
	@echo "  make seed        Cria um run Demo no banco e nos artefatos"
	@echo "  make detailed-doc Gera o DOCX técnico completo"
	@echo "  make detailed-pdf Gera o PDF do documento completo"
	@echo "  make deliverables Gera DOCX, PDF, slides e roteiro"
	@echo "  make screenshots  Captura as telas (requer stack no ar)"
	@echo "  make package      Gera o zip final em dist/"
	@echo "  make clean       Remove caches e artefatos de build"
	@echo "  make clean-pyc   Remove apenas caches do Python"

fetch:
	cd $(BACKEND) && $(PY) scripts/fetch_data.py --force

data-check:
	cd $(BACKEND) && $(PY) scripts/fetch_data.py --check

venv:
	$(PY) -m venv $(VENV)

install: venv
	$(VENV)/bin/pip install --upgrade pip
	cd $(BACKEND) && ../$(VENV)/bin/pip install -e ".[dev]"
	@echo "Ambiente pronto. Ative com: source $(VENV)/bin/activate"

test:
	cd $(BACKEND) && ../$(VENV)/bin/pytest -q

lint:
	cd $(BACKEND) && ../$(VENV)/bin/ruff check .

typecheck:
	cd $(BACKEND) && ../$(VENV)/bin/mypy nn api

types:
	cd $(BACKEND) && ../$(VENV)/bin/python scripts/export_openapi.py
	cd frontend && npm run types

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

refresh:
	$(COMPOSE) down --remove-orphans
	$(COMPOSE) up -d --build --force-recreate

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

db-shell:
	$(COMPOSE) exec db psql -U $${POSTGRES_USER:-tde} -d $${POSTGRES_DB:-tde}

reset-db:
	$(COMPOSE) down -v

seed:
	@if [ -x "$(VENV)/bin/python" ]; then \
		cd $(BACKEND) && ../$(VENV)/bin/python scripts/seed_demo.py; \
	else \
		$(COMPOSE) exec api python scripts/seed_demo.py; \
	fi

detailed-doc:
	cd $(BACKEND) && ../$(VENV)/bin/python scripts/build_detailed_doc.py

detailed-pdf: detailed-doc
	cd $(BACKEND) && ../$(VENV)/bin/python scripts/export_detailed_pdf.py

deliverables:
	cd $(BACKEND) && ../$(VENV)/bin/python scripts/build_deliverables.py

screenshots:
	cd frontend && SCREENSHOT_BASE_URL=$${SCREENSHOT_BASE_URL:-http://localhost:3000} node scripts/capture_screenshots.mjs

package: detailed-pdf deliverables
	cd $(BACKEND) && ../$(VENV)/bin/python scripts/package_delivery.py

clean: clean-pyc
	rm -rf frontend/.next frontend/out frontend/test-results frontend/playwright-report

clean-pyc:
	find $(BACKEND) -type d -name __pycache__ -prune -exec rm -rf {} +
	find $(BACKEND) -type d -name '*.egg-info' -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache $(BACKEND)/.pytest_cache $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache
