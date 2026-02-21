import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from pathlib import Path
from alembic import context

# --- 1. AJUSTE DE RUTA (PATH) ---
# Necesitamos que Alembic pueda "ver" tu carpeta 'src'.
# Esto agrega la carpeta raíz del proyecto al "camino" de Python.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# --- 2. IMPORTAR TU APP ---
# Ahora que Python ve la carpeta src, importamos tu Configuración y tus Modelos.
from src.config.config import DATABASE_URL
from src.bd.models import Base # Importante: Aquí están tus tablas (Licitacion, etc.)

# --- 3. CONFIGURACIÓN DE ALEMBIC ---
config = context.config

# Configurar el logger (para ver mensajes en consola)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- 4. CONEXIÓN A LA BASE DE DATOS ---
# AQUÍ ESTÁ LA CLAVE: Sobrescribimos la URL de 'alembic.ini' con la de tu 'config.py'.
# Así no tenemos que escribir la contraseña en el archivo .ini (que es inseguro).
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# --- 5. METADATA ---
# Le decimos a Alembic: "Compara la BD con ESTOS modelos"
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Correr migraciones sin conexión (poco común en tu caso)."""
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
    """Correr migraciones conectándose a la BD (Esto es lo que usaremos)."""
    
    # Crea el motor usando la configuración inyectada
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()