FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl é usado apenas pelo healthcheck do Compose.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# pyproject usa readme inline, então não é necessário copiar o README da raiz.
COPY pyproject.toml ./
COPY nn ./nn
COPY api ./api

RUN pip install --upgrade pip \
    && pip install .

COPY scripts ./scripts

RUN mkdir -p /app/data/raw /app/artifacts

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
