from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from src.bd.database import Base

class EstadoLicitacion(Base):
    """Modelo para almacenar los estados posibles de una licitación."""
    __tablename__ = "estados_licitacion"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(Integer, unique=True, nullable=False)
    descripcion = Column(String)
    
    licitaciones = relationship("Licitacion", back_populates="estado")


class Organismo(Base):
    """Modelo para almacenar las instituciones compradoras."""
    __tablename__ = "organismos"

    codigo = Column(String, primary_key=True, index=True)
    nombre = Column(String)
    puntaje = Column(Integer, default=0) 

    licitaciones = relationship("Licitacion", back_populates="organismo")


class Licitacion(Base):
    """Modelo principal que almacena la información de cada licitación."""
    __tablename__ = "licitaciones"

    id = Column(Integer, primary_key=True, index=True)
    codigo_externo = Column(String, unique=True, index=True)
    nombre = Column(String)
    descripcion = Column(Text, nullable=True)
    puntaje = Column(Integer, default=0)
    justificacion_puntaje = Column(Text, nullable=True)
    etapa = Column(String, default="candidata")
    detalle_productos = Column(Text, nullable=True)
    
    # Fechas
    fecha_cierre = Column(DateTime)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_publicacion = Column(DateTime, nullable=True)
    fecha_adjudicacion = Column(DateTime, nullable=True)
    
    # Relaciones y claves foráneas
    codigo_estado = Column(Integer, ForeignKey("estados_licitacion.codigo"))
    codigo_organismo = Column(String, ForeignKey("organismos.codigo"), nullable=True)
    
    # Bandera de control de descarga (False = Listado básico, True = Ficha completa)
    tiene_detalle = Column(Boolean, default=False) 

    estado = relationship("EstadoLicitacion", back_populates="licitaciones")
    organismo = relationship("Organismo", back_populates="licitaciones")


class PalabraClave(Base):
    """Modelo para las reglas de negocio y cálculo de puntajes."""
    __tablename__ = "palabras_claves"

    id = Column(Integer, primary_key=True, index=True)
    palabra = Column(String, nullable=False)
    categoria = Column(String, default="General")
    
    # Interruptores de búsqueda y asignación de puntaje
    puntaje_titulo = Column(Integer, default=0)
    puntaje_descripcion = Column(Integer, default=0)
    puntaje_productos = Column(Integer, default=0)

    def __repr__(self):
        return f"<PalabraClave(palabra='{self.palabra}', categoria='{self.categoria}')>"