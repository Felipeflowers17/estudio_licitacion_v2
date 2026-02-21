import os
from datetime import datetime
import pandas as pd
from src.bd.database import SessionLocal
from src.bd.models import Licitacion, PalabraClave, Organismo
from src.utils.logger import configurar_logger

logger = configurar_logger("servicio_exportador")

class ServicioExportador:
    """
    Gestiona la exportación de información desde la base de datos hacia 
    formatos de archivo plano (CSV) y hojas de cálculo (Excel).
    """

    def __init__(self, session_factory=SessionLocal):
        """Inyección de dependencia para asegurar aislamiento en pruebas unitarias."""
        self.session_factory = session_factory

    def generar_reporte(self, opciones: dict, directorio_destino: str) -> tuple:
        """
        Orquesta el proceso de exportación basado en las selecciones del usuario.
        Retorna una tupla con un booleano de éxito y un mensaje descriptivo.
        """
        marca_tiempo = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        carpeta_final = os.path.join(directorio_destino, f"Reporte_Licitaciones_{marca_tiempo}")
        
        try:
            os.makedirs(carpeta_final, exist_ok=True)
        except OSError as error_so:
            logger.error(f"Error del sistema operativo al crear carpeta: {error_so}")
            return False, f"Error creando el directorio de destino: {error_so}"

        # Mantenemos la conexión a la base de datos abierta de forma segura durante 
        # todo el ciclo de iteración de reportes
        with self.session_factory() as sesion:
            try:
                # Bloque 1: Exportación de Licitaciones filtradas por etapa
                if opciones.get('candidatas'):
                    consulta = sesion.query(Licitacion).filter(Licitacion.etapa == 'candidata')
                    self._exportar_consulta(sesion, "Candidatas", consulta, carpeta_final, opciones)

                if opciones.get('seguimiento'):
                    consulta = sesion.query(Licitacion).filter(Licitacion.etapa == 'seguimiento')
                    self._exportar_consulta(sesion, "Seguimiento", consulta, carpeta_final, opciones)

                if opciones.get('ofertadas'):
                    consulta = sesion.query(Licitacion).filter(Licitacion.etapa == 'ofertada')
                    self._exportar_consulta(sesion, "Ofertadas", consulta, carpeta_final, opciones)

                if opciones.get('full_db'):
                    consulta = sesion.query(Licitacion)
                    self._exportar_consulta(sesion, "Base_Completa", consulta, carpeta_final, opciones)

                # Bloque 2: Exportación de Reglas de Negocio
                if opciones.get('reglas'):
                    self._exportar_tabla_generica(sesion, "Reglas_Palabras", PalabraClave, carpeta_final, opciones)
                    self._exportar_tabla_generica(sesion, "Reglas_Organismos", Organismo, carpeta_final, opciones)

                logger.info(f"Exportación finalizada con éxito en {carpeta_final}")
                return True, f"Exportación exitosa. Archivos guardados en:\n{carpeta_final}"

            except Exception as error_critico:
                logger.error(f"Error crítico durante la exportación de datos: {error_critico}")
                return False, f"Ocurrió un error inesperado durante la exportación: {error_critico}"

    def _exportar_consulta(self, sesion, nombre_archivo: str, consulta, carpeta: str, opciones: dict):
        """Ejecuta una consulta SQL, limpia los datos y los envía a archivo."""
        dataframe = pd.read_sql(consulta.statement, sesion.connection())
        
        for columna in dataframe.select_dtypes(include=['datetimetz']).columns:
            dataframe[columna] = dataframe[columna].dt.tz_localize(None)

        self._guardar_archivos(dataframe, nombre_archivo, carpeta, opciones)

    def _exportar_tabla_generica(self, sesion, nombre_archivo: str, modelo, carpeta: str, opciones: dict):
        """Exporta el contenido completo de una tabla de configuración."""
        consulta = sesion.query(modelo)
        dataframe = pd.read_sql(consulta.statement, sesion.connection())
        self._guardar_archivos(dataframe, nombre_archivo, carpeta, opciones)

    def _guardar_archivos(self, dataframe, nombre_base: str, carpeta: str, opciones: dict):
        """Persiste el DataFrame en disco en los formatos solicitados."""
        if dataframe.empty:
            return 

        ruta_base = os.path.join(carpeta, nombre_base)

        if opciones.get('xlsx'):
            dataframe.to_excel(f"{ruta_base}.xlsx", index=False)
        
        if opciones.get('csv'):
            dataframe.to_csv(f"{ruta_base}.csv", index=False, sep=';', encoding='utf-8-sig')