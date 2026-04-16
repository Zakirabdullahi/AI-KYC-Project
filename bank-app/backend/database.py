import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Try multiple environment variables common on Vercel, Railway, and Heroku
SQLALCHEMY_DATABASE_URL = (
    os.getenv("POSTGRES_URL") or 
    os.getenv("POSTGRES_PRISMA_URL") or 
    os.getenv("DATABASE_URL") or 
    "sqlite:///./bank.db"
)

# If it's a postgres URL, we must ensure it uses the 'postgresql+psycopg2://' driver
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres"):
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Add SSL mode for Postgres if not present and on a cloud provider
if "postgresql" in SQLALCHEMY_DATABASE_URL and "sslmode" not in SQLALCHEMY_DATABASE_URL:
    if "?" in SQLALCHEMY_DATABASE_URL:
        SQLALCHEMY_DATABASE_URL += "&sslmode=require"
    else:
        SQLALCHEMY_DATABASE_URL += "?sslmode=require"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    pool_pre_ping=True,
    # SSL is handled via the URL usually, but connect_args is a fallback
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
