import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Try multiple environment variables common on Vercel
# POSTGRES_URL is provided by Vercel Postgres integration
# DATABASE_URL is standard for many Postgres providers
SQLALCHEMY_DATABASE_URL = (
    os.getenv("POSTGRES_URL") or 
    os.getenv("POSTGRES_PRISMA_URL") or 
    os.getenv("DATABASE_URL")
)

# If no cloud DB is found, fallback to SQLite (/tmp is the only writable dir on Vercel)
if not SQLALCHEMY_DATABASE_URL:
    if os.getenv("VERCEL"):
        SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/bank.db"
    else:
        SQLALCHEMY_DATABASE_URL = "sqlite:///./bank.db"

# Standardize the protocol for SQLAlchemy
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Ensure SSL is enabled for cloud Postgres (Neon requirement)
connect_args = {}
if "postgresql" in SQLALCHEMY_DATABASE_URL:
    # Neon and most cloud providers require SSL
    connect_args["sslmode"] = "require"
    
    # Check if we already have a query string
    if "?" not in SQLALCHEMY_DATABASE_URL:
        SQLALCHEMY_DATABASE_URL += "?sslmode=require"
    elif "sslmode" not in SQLALCHEMY_DATABASE_URL:
        SQLALCHEMY_DATABASE_URL += "&sslmode=require"
else:
    connect_args["check_same_thread"] = False

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    pool_pre_ping=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
