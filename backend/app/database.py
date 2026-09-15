
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./medimate.db"

    jwt_secret: str = "dev-only-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    app_name: str = "MediMate API"
    cors_origins: str = "*"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    **({"pool_pre_ping": True} if not settings.database_url.startswith("sqlite") else {})
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def create_db_and_tables() -> None:
    
    from . import models

    Base.metadata.create_all(bind=engine)

def get_db():
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()