"""API FastAPI do TDE (treino, histórico e simulador).

A API é a fonte única da verdade do projeto: importa ``nn`` para treinar
e serve o frontend Next.js em ``web/``.

Módulos previstos (Fase 5):
    main     — rotas REST e SSE
    schemas  — contratos pydantic
    trainer  — worker de treino (fila de 1)
    db       — engine e sessões SQLAlchemy
    models   — tabelas ``runs`` e ``run_epochs``
    store    — repositório e artefatos
"""

__version__ = "0.1.0"
