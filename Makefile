SHELL := /bin/bash
PY ?= python3

DATA := data/raw/datatran2024.csv

.DEFAULT_GOAL := help

.PHONY: help fetch data-check venv install clean-pyc

help:
	@echo "TDE Redes Neurais — alvos disponíveis:"
	@echo "  make fetch       Baixa e valida o CSV do DATATRAN 2024"
	@echo "  make data-check  Valida apenas o CSV local"
	@echo "  make venv        Cria o ambiente virtual .venv"
	@echo "  make install     Instala o projeto e as dependências de desenvolvimento"
	@echo "  make clean-pyc   Remove caches do Python"

fetch:
	$(PY) scripts/fetch_data.py --force

data-check:
	$(PY) scripts/fetch_data.py --check

venv:
	$(PY) -m venv .venv

install: venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"
	@echo "Ambiente pronto. Ative com: source .venv/bin/activate"

clean-pyc:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache
