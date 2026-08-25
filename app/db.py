from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(f"sqlite:///{settings.db_path}")


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
