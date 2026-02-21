from src.bd.database import SessionLocal
from src.bd.models import Organismo
from src.utils.logger import configurar_logger

logger = configurar_logger("controlador_organismos")

class ControladorOrganismos:
    """
    Gestiona las consultas y actualizaciones referidas a las instituciones compradoras.
    """
    
    def __init__(self, session_factory=SessionLocal):
        """
        Inicializa el controlador aplicando Inyección de Dependencias
        para facilitar el testing aislado y el manejo de sesiones seguras.
        """
        self.session_factory = session_factory
    
    def obtener_todos(self) -> list:
        """
        Recupera el listado completo de organismos ordenados alfabéticamente
        para facilitar su agrupación en la interfaz de usuario.
        """
        # Delegamos el cierre de la conexión al contexto 'with'
        with self.session_factory() as sesion:
            try:
                return sesion.query(Organismo).order_by(Organismo.nombre).all()
            except Exception as e:
                logger.error(f"Error cargando listado de organismos: {e}")
                return []

    def actualizar_puntaje(self, codigo_organismo: str, nuevo_puntaje: int) -> bool:
        """
        Modifica la valoración (positiva, negativa o neutra) de una institución
        para priorizar o penalizar sus futuras licitaciones.
        """
        with self.session_factory() as sesion:
            try:
                organismo = sesion.query(Organismo).filter_by(codigo=codigo_organismo).first()
                if organismo:
                    organismo.puntaje = nuevo_puntaje
                    sesion.commit()
                    return True
                return False
            except Exception as e:
                # Rollback preventivo ante cualquier fallo en la actualización
                sesion.rollback()
                logger.error(f"Error actualizando puntaje del organismo {codigo_organismo}: {e}")
                return False