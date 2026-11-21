SHELL := /bin/bash
PY ?= python3
VENV := .venv
BACKEND := backend

.DEFAULT_GOAL := help

.PHONY: help fetch data-check venv install test lint typecheck types clean-pyc

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
	@echo "  make clean-pyc   Remove caches do Python"

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

clean-pyc:
	find $(BACKEND) -type d -name __pycache__ -prune -exec rm -rf {} +
	find $(BACKEND) -type d -name '*.egg-info' -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache $(BACKEND)/.pytest_cache $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache
