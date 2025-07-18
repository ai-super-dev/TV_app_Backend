from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

# POSTGRES_USER = os.getenv("POSTGRES_USER")
# POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
# POSTGRES_DB = os.getenv("POSTGRES_DB")
# POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
# POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(
    os.getenv("SQLALCHEMY_DATABASE_URL"),
    pool_timeout=60,  # Increase timeout to 1 minute
    pool_recycle=2400,  # Recycle connections after 40 minutes
    pool_size=20,  # Number of connections to keep in the pool
    max_overflow=3,  # Allow additional connections if the pool is exhausted
    pool_pre_ping=True,  # Enable pre-ping to check if the connection is alive
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 

def delete_db(db: Session, model_class, record_id: int):
    record = db.query(model_class).filter(model_class.id == record_id).first()
    if record:
        db.delete(record)
        db.commit()
        return True
    return False

def update_db(db: Session, model_class, record_id: int, update_data: dict):
    record = db.query(model_class).filter(model_class.id == record_id).first()
    if record:
        for key, value in update_data.items():
            setattr(record, key, value)
        db.commit()
        db.refresh(record)
        return record
    return None
