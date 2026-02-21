from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config.config import DATABASE_URL

# Motor de la base de datos
engine = create_engine(DATABASE_URL, echo=False)

# Fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa para los modelos
Base = declarative_base()

def obtener_sesion_bd():
    """
    Generador utilitario para obtener una sesión de la base de datos.
    Maneja el ciclo de vida de la sesión asegurando su cierre automático.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()