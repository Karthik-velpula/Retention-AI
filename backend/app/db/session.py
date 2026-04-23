from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Ensure all ORM models are registered before the first query configures mappers.
import app.models  # noqa: E402,F401


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
