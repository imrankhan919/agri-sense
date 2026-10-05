from sqlmodel import Session, SQLModel, create_engine
from app.config import settings

engine = create_engine(settings.database_url, pool_size=10, max_overflow=20)

def create_db_and_tables() -> None:
    from app import models
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session