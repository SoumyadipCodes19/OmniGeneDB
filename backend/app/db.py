import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

default_db_path = "/app/data/omnigenedb.sqlite" if os.path.exists("/app/data") else "./omnigenedb.sqlite"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{default_db_path}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
