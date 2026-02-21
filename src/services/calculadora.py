import re
from src.bd.database import SessionLocal
from src.bd.models import PalabraClave, Organismo
from src.utils.logger import configurar_logger

logger = configurar_logger("calculadora_puntajes")

class CalculadoraPuntajes:
    """
    Servicio encargado de aplicar las reglas de negocio sobre los textos 
    de las licitaciones para determinar su viabilidad (puntaje).
    Implementa precisión léxica estricta mediante expresiones regulares 
    para erradicar falsos positivos por subcadenas.
    """

    def __init__(self, session_factory=SessionLocal):
        """
        Inicializa la calculadora inyectando la fábrica de sesiones.
        Carga inmediatamente las reglas en memoria para optimizar el rendimiento de evaluación.
        """
        self.session_factory = session_factory
        self.reglas_en_memoria = []
        self.cargar_reglas_negocio()

    def cargar_reglas_negocio(self):
        """Carga el diccionario completo de palabras clave desde la base de datos."""
        # Utilizamos el gestor de contexto para una lectura rápida, segura y que libere memoria
        with self.session_factory() as sesion:
            try:
                self.reglas_en_memoria = sesion.query(PalabraClave).all()
                logger.info(f"Reglas de negocio cargadas en memoria: {len(self.reglas_en_memoria)} ítems.")
            except Exception as error_carga:
                logger.error(f"Error al cargar las reglas de negocio: {error_carga}")
                self.reglas_en_memoria = []

    def evaluar_titulo(self, texto_titulo: str) -> tuple:
        """
        Analiza el nombre de la licitación buscando coincidencias exactas.
        Retorna: (puntaje_total, lista_de_motivos)
        """
        # Este método es puro y opera en RAM. No requiere apertura de conexión a BD.
        if not texto_titulo: 
            return 0, []
        
        puntaje_acumulado = 0
        registro_motivos = [] 
        texto_minusculas = texto_titulo.lower()
        
        for regla in self.reglas_en_memoria:
            if regla.puntaje_titulo != 0:
                # Búsqueda léxica estricta con fronteras de palabra (\b)
                patron = rf"\b{re.escape(regla.palabra.lower())}\b"
                if re.search(patron, texto_minusculas):
                    puntos = regla.puntaje_titulo
                    puntaje_acumulado += puntos
                    registro_motivos.append(f"[MATCH TÍTULO] '{regla.palabra}' ({puntos:+d})")
                    
        return puntaje_acumulado, registro_motivos

    def evaluar_detalle(self, codigo_organismo: str, descripcion: str, texto_productos: str) -> tuple:
        """
        Analiza la descripción técnica, los productos y el organismo comprador.
        Aplica evaluación léxica exacta para evitar falsos positivos.
        Retorna: (puntaje_total, lista_de_motivos)
        """
        puntaje_acumulado = 0
        registro_motivos = []
        
        # Apertura de sesión efímera y segura para consultar el catálogo de organismos
        with self.session_factory() as sesion:
            try:
                # 1. Evaluación por Organismo Comprador
                if codigo_organismo:
                    organismo_bd = sesion.query(Organismo).filter_by(codigo=codigo_organismo).first()
                    if organismo_bd and organismo_bd.puntaje != 0:
                        puntaje_acumulado += organismo_bd.puntaje
                        registro_motivos.append(f"[MATCH ORGANISMO] {organismo_bd.nombre} ({organismo_bd.puntaje:+d})")

                desc_minusculas = descripcion.lower() if descripcion else ""
                prod_minusculas = texto_productos.lower() if texto_productos else ""

                # 2. Evaluación Léxica Estricta por Palabras Clave
                for regla in self.reglas_en_memoria:
                    patron_busqueda = rf"\b{re.escape(regla.palabra.lower())}\b"

                    if regla.puntaje_descripcion != 0 and desc_minusculas:
                        if re.search(patron_busqueda, desc_minusculas):
                            puntaje_acumulado += regla.puntaje_descripcion
                            registro_motivos.append(f"[MATCH EXACTO DESC] '{regla.palabra}' ({regla.puntaje_descripcion:+d})")
                    
                    if regla.puntaje_productos != 0 and prod_minusculas:
                        if re.search(patron_busqueda, prod_minusculas):
                            puntaje_acumulado += regla.puntaje_productos
                            registro_motivos.append(f"[MATCH EXACTO PROD] '{regla.palabra}' ({regla.puntaje_productos:+d})")
                            
                return puntaje_acumulado, registro_motivos
                
            except Exception as error_evaluacion:
                logger.error(f"Error al evaluar los detalles profundos: {error_evaluacion}")
                return 0, []