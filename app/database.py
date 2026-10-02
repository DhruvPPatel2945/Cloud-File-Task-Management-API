import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# use env variable or default local db
# NOTE: host port is 5433 because a local Windows PostgreSQL install
# already occupies 5432 (see docker-compose.yml). Container port is 5432.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5433/task_api"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()