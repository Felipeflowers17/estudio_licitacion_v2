import traceback
from PySide6.QtCore import QThread, Signal

from src.services.exportador import ServicioExportador
from src.utils.logger import configurar_logger

logger = configurar_logger("trabajador_exportacion")


class TrabajadorExportacion(QThread):
    """
    Hilo de ejecución dedicado a envolver el proceso de exportación de datos.
    
    Responsabilidad única: ejecutar ServicioExportador.generar_reporte() en un
    hilo separado para evitar el bloqueo de la interfaz gráfica durante
    operaciones de lectura masiva desde la base de datos y escritura en disco.
    
    Emite 'finalizado' con (bool, str): éxito y mensaje descriptivo para la UI.
    """
    finalizado = Signal(bool, str)

    def __init__(self, opciones: dict, directorio_destino: str):
        super().__init__()
        self.opciones = opciones
        self.directorio_destino = directorio_destino
        self.servicio = ServicioExportador()

    def run(self):
        try:
            exito, mensaje = self.servicio.generar_reporte(
                self.opciones,
                self.directorio_destino
            )
            self.finalizado.emit(exito, mensaje)

        except Exception as error_general:
            mensaje_error = f"Falla crítica en el hilo de exportación: {str(error_general)}"
            logger.error(f"{mensaje_error}\n{traceback.format_exc()}")
            self.finalizado.emit(False, mensaje_error)