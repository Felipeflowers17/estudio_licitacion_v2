from src.bd.database import SessionLocal
from src.bd.models import PalabraClave
from src.utils.logger import configurar_logger
from src.services.instancias import calculadora_compartida

logger = configurar_logger("controlador_puntajes")


class ControladorPuntajes:
    """
    Administra el diccionario de reglas de negocio (palabras clave y sus pesos)
    utilizado por la calculadora para evaluar automáticamente las licitaciones.
    
    Responsabilidad adicional: Después de cada operación de escritura exitosa,
    notifica a la instancia compartida de CalculadoraPuntajes para que recargue
    sus reglas desde la BD, garantizando que el motor de scoring esté siempre
    sincronizado con la configuración actual del usuario.
    """

    def __init__(self, session_factory=SessionLocal):
        """
        Inicializa el controlador con inyección de dependencias.
        La calculadora compartida se importa de forma lazy (dentro de los métodos)
        para evitar importaciones circulares durante el arranque de la aplicación.
        """
        self.session_factory = session_factory

    def _recargar_calculadora(self):
        """
        Recarga las reglas de negocio en la instancia compartida de la calculadora.
        
        Se llama después de cada operación de escritura exitosa (guardar o borrar).
        Usa importación local para evitar dependencias circulares en el arranque,
        ya que instancias.py importa calculadora.py que importa database.py.
        """
        try:
            calculadora_compartida.cargar_reglas_negocio()
            logger.info("Reglas de negocio recargadas en la calculadora compartida.")
        except Exception as e:
            # No interrumpimos el flujo principal si la recarga falla.
            # El usuario ya guardó sus datos correctamente; el error es solo de sincronización.
            logger.error(f"No se pudo recargar la calculadora tras modificar reglas: {e}")

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
        Inserta una nueva regla o actualiza una existente.
        Tras el commit exitoso, recarga la calculadora compartida para que
        la nueva regla sea evaluada inmediatamente en la próxima extracción.
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

                # La BD ya tiene los datos correctos. Ahora sincronizamos la RAM.
                self._recargar_calculadora()
                return True

            except Exception as e:
                sesion.rollback()
                logger.error(f"Error guardando configuración de la palabra '{palabra}': {e}")
                return False

    def borrar_palabra(self, id_palabra: int) -> bool:
        """
        Elimina permanentemente una regla de negocio del sistema.
        Tras el commit exitoso, recarga la calculadora para que la palabra
        eliminada deje de influir en las evaluaciones inmediatamente.
        """
        with self.session_factory() as sesion:
            try:
                item = sesion.get(PalabraClave, id_palabra)
                if item:
                    sesion.delete(item)
                    sesion.commit()

                    # Sincronizamos la RAM con el estado actual de la BD.
                    self._recargar_calculadora()
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