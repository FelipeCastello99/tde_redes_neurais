import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import time

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://tde:tde@localhost:5432/tde")

def get_engine():
    retries = 5
    while retries > 0:
        try:
            engine = create_engine(
                DATABASE_URL,
                poolclass=QueuePool,
                pool_pre_ping=True,
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except Exception as e:
            print(f"Banco não pronto ({retries} tentativas restantes): {e}")
            time.sleep(2)
            retries -= 1
    raise ConnectionError("Não foi possível conectar ao banco")

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
