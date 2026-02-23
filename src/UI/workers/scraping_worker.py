import time
import traceback
from datetime import timedelta
from PySide6.QtCore import QThread, Signal

from src.utils.logger import configurar_logger
from src.services.orquestador import OrquestadorIngesta

logger = configurar_logger("trabajador_extraccion")

class TrabajadorExtraccion(QThread):
    """
    Hilo de ejecución responsable de envolver el orquestador de ingesta masiva.
    """
    progreso = Signal(str)
    finalizado = Signal()
    error = Signal(str)

    def __init__(self, fecha_inicio, fecha_fin):
        super().__init__()
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.ejecutando = True
        self.orquestador = OrquestadorIngesta()

    def run(self):
        try:
            def reportar_progreso(mensaje):
                self.progreso.emit(mensaje)

            def verificar_ejecucion():
                return self.ejecutando

            estadisticas = self.orquestador.procesar_rango_fechas(
                self.fecha_inicio,
                self.fecha_fin,
                callback_progreso=reportar_progreso,
                verificador_ejecucion=verificar_ejecucion
            )

            self.progreso.emit(f"\n{'='*60}")
            self.progreso.emit("[SISTEMA] PROCESO DE EXTRACCIÓN COMPLETADO")
            self.progreso.emit(f"{'='*60}")
            self.progreso.emit("[INFO] Totales Globales de la Operación:")
            self.progreso.emit(f"   - Descargas exitosas: {estadisticas['detalles_exitosos']}")
            self.progreso.emit(f"   - Elementos pendientes: {estadisticas['detalles_pendientes']}")
            self.progreso.emit(f"   - Elementos ignorados: {estadisticas['detalles_omitidos']}")
            self.finalizado.emit()

        except Exception as error_general:
            self.error.emit(f"Falla crítica en el hilo de trabajo: {str(error_general)}")
            logger.error(f"Excepción en TrabajadorExtraccion: {error_general}\n{traceback.format_exc()}")
            
    def stop(self):
        self.ejecutando = False
        self.progreso.emit("[SISTEMA] Iniciando secuencia de detención. Espere a que finalice el ciclo actual...")
        
class TrabajadorExtraccionManual(QThread):
    """
    Hilo dedicado exclusivamente a envolver la ejecución del orquestador 
    de ingesta manual, evitando el bloqueo de la interfaz principal.
    """
    progreso = Signal(str)
    finalizado = Signal(bool, str) 

    def __init__(self, codigo: str, etapa_destino: str):
        super().__init__()
        self.codigo = codigo
        self.etapa_destino = etapa_destino
        self.orquestador = OrquestadorIngesta()

    def run(self):
        # Creamos una función adaptadora para conectar el callback puro de Python
        # con el sistema de señales de PySide6
        def reportar_progreso(mensaje):
            self.progreso.emit(mensaje)
        
        exito, mensaje = self.orquestador.procesar_licitacion_manual(
            self.codigo, 
            self.etapa_destino, 
            callback_progreso=reportar_progreso
        )
        
        self.finalizado.emit(exito, mensaje)