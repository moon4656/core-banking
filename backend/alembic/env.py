import os
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

from app.models import knowledge_model, agent_model, trace_model, eval_model, monitor_model, strategy_model  # noqa: F401 — registers models with Base
from app.core.database import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
