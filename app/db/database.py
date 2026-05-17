import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database URL from environment, fall back to local PostgreSQL for development
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:admin@localhost:5432/messenger_db"
)

# Only require SSL if we are NOT connecting to localhost / 127.0.0.1
if "localhost" in DATABASE_URL or "127.0.0.1" in DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"sslmode": "require"}
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()