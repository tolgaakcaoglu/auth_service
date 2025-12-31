from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings
from .base import Base

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def init_db():
    # Create tables (simple approach). For production use migrations (alembic).
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
