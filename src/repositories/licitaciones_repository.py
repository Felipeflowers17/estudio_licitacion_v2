from sqlalchemy.orm import joinedload
from sqlalchemy import or_
from src.bd.database import SessionLocal
from src.bd.models import Licitacion
from src.utils.logger import configurar_logger
from src.config.constantes import (
    ESTADO_LICITACION_ACTIVA,
    LIMITE_LICITACIONES_ACTIVAS,
    LIMITE_CANDIDATAS_VISIBLES,
    UMBRAL_PUNTAJE_CANDIDATA,
    EtapaLicitacion
)

logger = configurar_logger("repositorio_licitaciones")


class RepositorioLicitaciones:
    """
    Gestiona las transacciones y consultas de base de datos para las licitaciones.
    Centraliza la lógica de filtrado y cambio de etapas del modelo MVC.
    """

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def obtener_licitaciones_activas(self) -> list:
        with self.session_factory() as sesion:
            try:
                resultados = sesion.query(Licitacion)\
                    .options(joinedload(Licitacion.estado))\
                    .filter(Licitacion.codigo_estado == ESTADO_LICITACION_ACTIVA)\
                    .order_by(Licitacion.puntaje.desc())\
                    .limit(LIMITE_LICITACIONES_ACTIVAS).all()
                return resultados
            except Exception as e:
                logger.error(f"Error consultando licitaciones activas: {e}")
                return []

    def mover_licitacion(self, codigo_externo: str, nueva_etapa: str) -> bool:
        """
        Transfiere una licitación específica hacia una nueva etapa del flujo.
        Se espera que 'nueva_etapa' provenga de EtapaLicitacion.XXX.value
        """
        with self.session_factory() as sesion:
            try:
                licitacion = sesion.query(Licitacion).filter_by(codigo_externo=codigo_externo).first()
                if licitacion:
                    licitacion.etapa = nueva_etapa
                    sesion.commit()
                    return True
                return False
            except Exception as e:
                sesion.rollback()
                logger.error(f"Error al mover la licitación {codigo_externo} a {nueva_etapa}: {e}")
                return False

    def obtener_candidatas(self) -> list:
        with self.session_factory() as sesion:
            try:
                resultados = sesion.query(Licitacion)\
                    .options(joinedload(Licitacion.estado))\
                    .filter(Licitacion.puntaje > UMBRAL_PUNTAJE_CANDIDATA)\
                    .filter(or_(Licitacion.etapa == EtapaLicitacion.CANDIDATA.value, Licitacion.etapa == None))\
                    .order_by(Licitacion.puntaje.desc())\
                    .limit(LIMITE_CANDIDATAS_VISIBLES).all()
                return resultados
            except Exception as e:
                logger.error(f"Error obteniendo candidatas: {e}")
                return []

    def obtener_seguimiento(self) -> list:
        with self.session_factory() as sesion:
            try:
                return sesion.query(Licitacion)\
                    .options(joinedload(Licitacion.estado))\
                    .filter(Licitacion.etapa == EtapaLicitacion.SEGUIMIENTO.value)\
                    .order_by(Licitacion.puntaje.desc())\
                    .all()
            except Exception as e:
                logger.error(f"Error obteniendo licitaciones en seguimiento: {e}")
                return []

    def obtener_ofertadas(self) -> list:
        with self.session_factory() as sesion:
            try:
                return sesion.query(Licitacion)\
                    .options(joinedload(Licitacion.estado))\
                    .filter(Licitacion.etapa == EtapaLicitacion.OFERTADA.value)\
                    .order_by(Licitacion.puntaje.desc())\
                    .all()
            except Exception as e:
                logger.error(f"Error obteniendo licitaciones ofertadas: {e}")
                return []

    def obtener_licitacion_por_codigo(self, codigo_externo: str):
        with self.session_factory() as sesion:
            try:
                return sesion.query(Licitacion)\
                    .options(joinedload(Licitacion.estado), joinedload(Licitacion.organismo))\
                    .filter_by(codigo_externo=codigo_externo)\
                    .first()
            except Exception as e:
                logger.error(f"Error buscando detalle de licitación {codigo_externo}: {e}")
                return None