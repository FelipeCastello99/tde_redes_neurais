import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://tde:tde@localhost:5432/tde",
)

# A engine é criada de forma preguiçosa: importar ``api.main`` para gerar o
# OpenAPI não deve exigir um Postgres de pé. A conexão é validada no startup.
_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_pre_ping=True,
        )
    return _engine


def wait_for_database(retries: int = 10, delay: float = 2.0) -> None:
    """Aguarda o Postgres aceitar conexões (usado no startup da API)."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as exc:  # pragma: no cover - depende do ambiente
            last_error = exc
            if attempt < retries - 1:
                time.sleep(delay)
    raise ConnectionError(f"não foi possível conectar ao banco: {last_error}")


def get_session_factory():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
