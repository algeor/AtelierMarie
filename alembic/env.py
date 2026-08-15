import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Resolve the database URL WITHOUT importing the app's full Settings. Running a
# migration must not require unrelated production secrets (ADMIN_API_KEY,
# JWT_SECRET, ...) that Settings validation would demand in environment=production
# — otherwise `alembic upgrade head` in a minimal migration/CI context refuses to
# run. Prefer the URL injected by programmatic callers / the test harness via
# config.attributes, then a dedicated migration URL (env var or file-backed
# secret, mirroring Settings.migration_database_url), then the DATABASE_URL env
# var (or its file-backed secret) for plain CLI usage.
def _resolve_migration_database_url() -> str | None:
    from_attributes = config.attributes.get("database_url")
    if from_attributes:
        return from_attributes
    for env_var, file_env_var in (
        ("MIGRATION_DATABASE_URL", "MIGRATION_DATABASE_URL_FILE"),
        ("DATABASE_URL", "DATABASE_URL_FILE"),
    ):
        value = os.environ.get(env_var)
        if value:
            return value
        file_path = os.environ.get(file_env_var)
        if file_path:
            return Path(file_path).read_text(encoding="utf-8").strip()
    return None


database_url = _resolve_migration_database_url()
if not database_url:
    raise RuntimeError(
        "No migration database URL is set. Provide it via config.attributes"
        "['database_url'], the MIGRATION_DATABASE_URL / DATABASE_URL environment "
        "variable, or their *_FILE file-backed secret variants before running "
        "migrations."
    )

if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)

config.set_main_option("sqlalchemy.url", database_url)
# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
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
