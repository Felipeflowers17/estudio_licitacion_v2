import re
import threading
from src.bd.database import SessionLocal
from src.bd.models import PalabraClave
from src.utils.logger import configurar_logger

logger = configurar_logger("calculadora_puntajes")

class CalculadoraPuntajes:
    """
    Servicio encargado de aplicar las reglas de negocio sobre los textos.
    Implementa precompilación de expresiones regulares para evitar 
    cuellos de botella de CPU durante el procesamiento masivo.
    
    Implementa Thread Safety (Lock) para permitir la recarga en caliente
    de reglas de negocio sin colisionar con hilos de evaluación en segundo plano.
    """

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory
        self.reglas_compiladas = []
        # Candado de exclusión mutua (Mutex) para operaciones seguras entre hilos
        self.cerrojo = threading.Lock()
        self.cargar_reglas_negocio()

    def cargar_reglas_negocio(self):
        """
        Carga las reglas y precompila los patrones de búsqueda léxica.
        Se construye la nueva lista en memoria y luego se intercambia de forma
        atómica mediante el cerrojo para no interrumpir evaluaciones en curso.
        """
        with self.session_factory() as sesion:
            try:
                reglas_bd = sesion.query(PalabraClave).all()
                nuevas_reglas = []
                
                for regla in reglas_bd:
                    patron_texto = rf"\b{re.escape(regla.palabra.lower())}\b"
                    patron_compilado = re.compile(patron_texto)
                    nuevas_reglas.append((regla, patron_compilado))
                    
                # Bloque crítico: Intercambio seguro de la lista en memoria
                with self.cerrojo:
                    self.reglas_compiladas = nuevas_reglas
                    
                logger.info(f"Reglas de negocio cargadas y precompiladas: {len(self.reglas_compiladas)} ítems.")
            except Exception as error_carga:
                logger.error(f"Error al cargar las reglas de negocio: {error_carga}")
                with self.cerrojo:
                    self.reglas_compiladas = []

    def evaluar_titulo(self, texto_titulo: str) -> tuple:
        """
        Analiza el nombre de la licitación iterando sobre los patrones ya precompilados.
        """
        if not texto_titulo: 
            return 0, []
        
        puntaje_acumulado = 0
        registro_motivos = [] 
        texto_minusculas = texto_titulo.lower()
        
        # Bloque crítico: Copia rápida (shallow copy) para iterar sin bloquear la lista original
        with self.cerrojo:
            reglas_locales = list(self.reglas_compiladas)
        
        for regla, patron in reglas_locales:
            if regla.puntaje_titulo != 0:
                if patron.search(texto_minusculas):
                    puntos = regla.puntaje_titulo
                    puntaje_acumulado += puntos
                    registro_motivos.append(f"[MATCH TÍTULO] '{regla.palabra}' ({puntos:+d})")
                    
        return puntaje_acumulado, registro_motivos

    def evaluar_detalle(self, descripcion: str, texto_productos: str) -> tuple:
        """
        Analiza descripción y productos utilizando patrones precompilados.
        Se ha removido la consulta a la base de datos para garantizar que esta
        sea una función pura (CPU-bound) y mejorar el rendimiento.
        """
        puntaje_acumulado = 0
        registro_motivos = []
        
        try:
            desc_minusculas = descripcion.lower() if descripcion else ""
            prod_minusculas = texto_productos.lower() if texto_productos else ""

            # Bloque crítico: Copia rápida (shallow copy) para lectura segura
            with self.cerrojo:
                reglas_locales = list(self.reglas_compiladas)

            for regla, patron in reglas_locales:
                if regla.puntaje_descripcion != 0 and desc_minusculas:
                    if patron.search(desc_minusculas):
                        puntaje_acumulado += regla.puntaje_descripcion
                        registro_motivos.append(f"[MATCH EXACTO DESC] '{regla.palabra}' ({regla.puntaje_descripcion:+d})")
                
                if regla.puntaje_productos != 0 and prod_minusculas:
                    if patron.search(prod_minusculas):
                        puntaje_acumulado += regla.puntaje_productos
                        registro_motivos.append(f"[MATCH EXACTO PROD] '{regla.palabra}' ({regla.puntaje_productos:+d})")
                        
            return puntaje_acumulado, registro_motivos
            
        except Exception as error_evaluacion:
            logger.error(f"Error al evaluar los detalles profundos: {error_evaluacion}")
            return 0, []