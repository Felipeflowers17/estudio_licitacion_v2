from src.bd.database import SessionLocal
from src.bd.models import PalabraClave
from src.utils.logger import configurar_logger

logger = configurar_logger("controlador_puntajes")

class ControladorPuntajes:
    """
    Administra el diccionario de reglas de negocio (palabras clave y sus pesos)
    utilizado por la calculadora para evaluar automáticamente las licitaciones.
    """
    
    def __init__(self, session_factory=SessionLocal):
        """
        Inicializa el controlador con inyección de dependencias para delegar 
        la creación y el ciclo de vida de la sesión de base de datos.
        """
        self.session_factory = session_factory
    
    def obtener_todas_palabras(self) -> list:
        """Recupera la totalidad de las reglas configuradas."""
        with self.session_factory() as sesion:
            try:
                return sesion.query(PalabraClave).all()
            except Exception as e:
                logger.error(f"Error obteniendo palabras claves: {e}")
                return []

    def guardar_palabra(self, id_palabra: int, palabra: str, categoria: str, 
                        p_titulo: int, p_desc: int, p_prod: int) -> bool:
        """
        Inserta una nueva regla de negocio o actualiza una existente 
        si se proporciona su identificador.
        """
        with self.session_factory() as sesion:
            try:
                if id_palabra:
                    item = sesion.get(PalabraClave, id_palabra)
                    if item:
                        item.palabra = palabra
                        item.categoria = categoria
                        item.puntaje_titulo = p_titulo
                        item.puntaje_descripcion = p_desc
                        item.puntaje_productos = p_prod
                else:
                    nuevo_item = PalabraClave(
                        palabra=palabra,
                        categoria=categoria,
                        puntaje_titulo=p_titulo,
                        puntaje_descripcion=p_desc,
                        puntaje_productos=p_prod
                    )
                    sesion.add(nuevo_item)
                
                sesion.commit()
                return True
            except Exception as e:
                sesion.rollback()
                logger.error(f"Error guardando configuración de la palabra '{palabra}': {e}")
                return False

    def borrar_palabra(self, id_palabra: int) -> bool:
        """Elimina permanentemente una regla de negocio del sistema."""
        with self.session_factory() as sesion:
            try:
                item = sesion.get(PalabraClave, id_palabra)
                if item:
                    sesion.delete(item)
                    sesion.commit()
                    return True
                return False
            except Exception as e:
                sesion.rollback()
                logger.error(f"Error borrando palabra clave ID {id_palabra}: {e}")
                return False
            
    def obtener_palabra_por_id(self, id_palabra: int):
        """Recupera una regla de negocio específica por su ID."""
        with self.session_factory() as sesion:
            try:
                item = sesion.get(PalabraClave, id_palabra)
                if item:
                    sesion.expunge(item) 
                return item
            except Exception as e:
                logger.error(f"Error obteniendo palabra ID {id_palabra}: {e}")
                return None