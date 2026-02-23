import os
from datetime import datetime
import pandas as pd
from src.bd.database import SessionLocal
from src.bd.models import Licitacion, PalabraClave, Organismo
from src.utils.logger import configurar_logger
from src.config.constantes import EtapaLicitacion, TAMANIO_CHUNK_EXPORTACION

logger = configurar_logger("servicio_exportador")

class ServicioExportador:
    """
    Gestiona la exportación de información desde la base de datos hacia 
    formatos de archivo plano (CSV) y hojas de cálculo (Excel).
    
    Implementa procesamiento por lotes (Chunking) para garantizar un
    consumo de memoria RAM constante y prevenir bloqueos del sistema.
    """

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def generar_reporte(self, opciones: dict, directorio_destino: str) -> tuple:
        """
        Orquesta el proceso de exportación basado en las selecciones del usuario.
        """
        marca_tiempo = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        carpeta_final = os.path.join(directorio_destino, f"Reporte_Licitaciones_{marca_tiempo}")
        
        try:
            os.makedirs(carpeta_final, exist_ok=True)
        except OSError as error_so:
            logger.error(f"Error al crear carpeta: {error_so}")
            return False, f"Error creando el directorio: {error_so}"

        with self.session_factory() as sesion:
            try:
                # Diccionario de mapeo: Entidad -> Consulta SQLAlchemy
                consultas = {
                    'candidatas': sesion.query(Licitacion).filter(Licitacion.etapa == EtapaLicitacion.CANDIDATA.value),
                    'seguimiento': sesion.query(Licitacion).filter(Licitacion.etapa == EtapaLicitacion.SEGUIMIENTO.value),
                    'ofertadas': sesion.query(Licitacion).filter(Licitacion.etapa == EtapaLicitacion.OFERTADA.value),
                    'full_db': sesion.query(Licitacion)
                }

                for clave, consulta in consultas.items():
                    if opciones.get(clave):
                        self._procesar_exportacion_masiva(sesion, clave.capitalize(), consulta, carpeta_final, opciones)

                if opciones.get('reglas'):
                    self._procesar_exportacion_masiva(sesion, "Reglas_Palabras", sesion.query(PalabraClave), carpeta_final, opciones)
                    self._procesar_exportacion_masiva(sesion, "Reglas_Organismos", sesion.query(Organismo), carpeta_final, opciones)

                return True, f"Exportación exitosa en:\n{carpeta_final}"

            except Exception as error_critico:
                logger.error(f"Error crítico en exportación: {error_critico}")
                return False, f"Falla inesperada: {error_critico}"

    def _procesar_exportacion_masiva(self, sesion, nombre: str, consulta, carpeta: str, opciones: dict):
        """
        Ejecuta la lectura incremental de la base de datos y delega la escritura.
        """
        # El parámetro chunksize convierte a read_sql en un generador de DataFrames
        lector_chunks = pd.read_sql(
            consulta.statement, 
            sesion.connection(), 
            chunksize=TAMANIO_CHUNK_EXPORTACION
        )

        es_primer_bloque = True
        ruta_base = os.path.join(carpeta, nombre)

        # Para Excel, debido a las limitaciones del formato, acumulamos de forma controlada
        # Para CSV, escribimos de forma incremental directamente en el disco
        datos_excel = [] if opciones.get('xlsx') else None

        for chunk in lector_chunks:
            # Limpieza de zonas horarias para compatibilidad con Excel
            for col in chunk.select_dtypes(include=['datetimetz']).columns:
                chunk[col] = chunk[col].dt.tz_localize(None)

            # Exportación incremental a CSV (Anexado al final del archivo)
            if opciones.get('csv'):
                self._escribir_csv_incremental(chunk, f"{ruta_base}.csv", es_primer_bloque)
            
            # Recolección para Excel
            if datos_excel is not None:
                datos_excel.append(chunk)

            es_primer_bloque = False

        # Escritura final de Excel (se ejecuta una sola vez al final del flujo de datos)
        if datos_excel:
            df_final = pd.concat(datos_excel, ignore_index=True)
            df_final.to_excel(f"{ruta_base}.xlsx", index=False)
            del df_final # Liberación explícita de memoria

    def _escribir_csv_incremental(self, dataframe, ruta: str, incluir_cabecera: bool):
        """Escribe el lote actual al final del archivo CSV sin cargar el resto del archivo."""
        dataframe.to_csv(
            ruta,
            mode='a',             # Modo 'append' (anexar)
            index=False,
            sep=';',
            encoding='utf-8-sig',
            header=incluir_cabecera # Solo pone los títulos de columna en el primer bloque
        )