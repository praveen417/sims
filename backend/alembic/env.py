import os
import sys

# make the 'app' package importable no matter how alembic is launched
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import context
from sqlalchemy import create_engine

from app.config import settings
from app.database import Base
from app import models  # noqa: F401

target_metadata = Base.metadata


def run_migrations_online():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
