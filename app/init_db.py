from .database import engine, Base
from . import models  # noqa: F401  (ensures models are registered)

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized: users.db")
