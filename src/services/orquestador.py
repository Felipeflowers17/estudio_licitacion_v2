import time
from datetime import timedelta

from src.scraper.recolector import RecolectorMercadoPublico
from src.services.almacenar import AlmacenadorLicitaciones
from src.repositories.licitaciones_repository import RepositorioLicitaciones
from src.services.instancias import calculadora_compartida
from src.utils.logger import configurar_logger
from src.config.constantes import PAUSA_ENTRE_DIAS_EXTRACCION, UMBRAL_PUNTAJE_CANDIDATA, EtapaLicitacion
from src.services.transformador_api import TransformadorAPI
from src.bd.database import SessionLocal
from src.bd.models import Organismo

logger = configurar_logger("orquestador_ingesta")


class OrquestadorIngesta:
    """
    Servicio de aplicación que coordina el flujo completo de extracción,
    evaluación y persistencia de licitaciones.
    
    Implementa el patrón Facade: la interfaz gráfica solo interactúa con este
    servicio sin necesitar conocer los detalles de cada componente interno.
    
    Usa la instancia compartida de CalculadoraPuntajes para garantizar que
    cualquier cambio en las reglas de negocio (hecho por el usuario desde la UI)
    se refleje inmediatamente en las evaluaciones sin reiniciar la aplicación.
    """

    def __init__(self):
        self.recolector = RecolectorMercadoPublico()
        self.almacenador = AlmacenadorLicitaciones()
        self.repositorio = RepositorioLicitaciones()
        # Usamos la referencia a la instancia compartida, no una nueva instancia.
        self.calculadora = calculadora_compartida
        # Caché local para evitar consultas N+1 a la base de datos
        self.cache_organismos = {}

    def _cargar_cache_organismos(self) -> dict:
        """Carga en RAM los puntajes de los organismos para evitar consultas N+1."""
        with SessionLocal() as sesion:
            try:
                organismos = sesion.query(Organismo).all()
                return {org.codigo: org.puntaje for org in organismos}
            except Exception as e:
                logger.error(f"Error cargando caché de organismos: {e}")
                return {}

    # =========================================================================
    # PROCESAMIENTO MANUAL (Una sola licitación por código)
    # =========================================================================

    def procesar_licitacion_manual(self, codigo: str, etapa_destino: str,
                                   callback_progreso=None) -> tuple[bool, str]:
        """
        Descarga, evalúa y almacena una licitación específica por su código.
        """
        def emitir(mensaje: str):
            if callback_progreso:
                callback_progreso(mensaje)

        try:
            # Aseguramos que la caché esté disponible incluso para procesos manuales
            if not self.cache_organismos:
                self.cache_organismos = self._cargar_cache_organismos()

            emitir("Consultando API de Mercado Público...")
            resultado = self.recolector.obtener_detalle_licitacion(codigo)

            if resultado['estado'] != 'exitoso' or not resultado.get('datos'):
                return False, (
                    f"No fue posible encontrar la licitación '{codigo}'.\n"
                    f"Estado reportado por la API: {resultado['estado']}"
                )

            datos_api = resultado['datos']

            emitir("Evaluando reglas de negocio...")
            titulo = datos_api.get("Nombre", "")
            puntaje_inicial, motivos = self.calculadora.evaluar_titulo(titulo)

            comprador = datos_api.get("Comprador", {})
            cod_org = comprador.get("CodigoOrganismo", "")
            desc = datos_api.get("Descripcion", "")
            items_str = self._extraer_texto_items(datos_api)

            # Evaluación de detalle (función pura)
            puntaje_detalle, motivos_detalle = self.calculadora.evaluar_detalle(
                desc, items_str
            )

            # Sumatoria final incluyendo el puntaje del organismo desde caché
            puntaje_org_cache = self.cache_organismos.get(cod_org, 0)
            puntaje_total = puntaje_inicial + puntaje_detalle + puntaje_org_cache

            motivos_completos = motivos + motivos_detalle
            if puntaje_org_cache != 0:
                motivos_completos.append(f"[MATCH ORGANISMO] Puntaje institucional ({puntaje_org_cache:+d})")

            # Inyección de metadatos calculados en el diccionario original de la API
            datos_api["_PuntajeCalculado"] = puntaje_total
            datos_api["_Justificacion"] = "\n".join(motivos_completos)
            datos_api["_TieneDetalle"] = True
            datos_api["_EtapaAsignada"] = etapa_destino

            emitir("Guardando en base de datos...")
            self.almacenador.guardar_licitacion_individual(datos_api)
            self.repositorio.mover_licitacion(codigo, etapa_destino)

            return True, f"La licitación '{codigo}' fue procesada y movida a '{etapa_destino}' exitosamente."

        except Exception as e:
            logger.error(f"Error en orquestador manual para '{codigo}': {e}")
            return False, f"Ocurrió un error inesperado al procesar la licitación:\n{str(e)}"

    # =========================================================================
    # PROCESAMIENTO MASIVO (Rango de fechas)
    # =========================================================================

    def procesar_rango_fechas(self, fecha_inicio, fecha_fin,
                              callback_progreso=None,
                              verificador_ejecucion=None) -> dict:
        """
        Orquesta la descarga masiva de licitaciones en un rango de fechas.
        """
        def emitir(mensaje: str):
            if callback_progreso:
                callback_progreso(mensaje)

        def debe_continuar() -> bool:
            if verificador_ejecucion:
                return verificador_ejecucion()
            return True

        estadisticas = {
            'licitaciones_basicas': 0,
            'detalles_exitosos': 0,
            'detalles_pendientes': 0,
            'detalles_omitidos': 0,
            'errores': 0
        }

        # CARGA DE CACHÉ INICIAL: Evita miles de consultas SELECT durante el proceso
        emitir("[SISTEMA] Sincronizando directorio de organismos en memoria...")
        self.cache_organismos = self._cargar_cache_organismos()

        dias_totales = (fecha_fin - fecha_inicio).days + 1
        emitir(f"[INFO] Iniciando proceso para {dias_totales} día(s).")

        for i in range(dias_totales):
            if not debe_continuar():
                emitir("[WARNING] Proceso interrumpido por el usuario.")
                break

            fecha_actual = fecha_inicio + timedelta(days=i)
            fecha_log = fecha_actual.strftime("%d-%m-%Y")
            str_fecha = fecha_actual.strftime("%d%m%Y")

            emitir(f"\n{'='*60}")
            emitir(f"[PROCESANDO] Día {i+1}/{dias_totales} - Fecha: {fecha_log}")
            emitir(f"{'='*60}")

            licitaciones = self.recolector.obtener_licitaciones_diarias(
                fecha_cadena=str_fecha
            )

            if not licitaciones:
                emitir(f"[INFO] No se registraron licitaciones para {fecha_log}.")
                continue

            total_dia = len(licitaciones)
            estadisticas['licitaciones_basicas'] += total_dia
            emitir(f"[INFO] {total_dia} licitaciones detectadas. Iniciando análisis...")

            stats_dia = self._procesar_listado_diario(
                licitaciones, total_dia, emitir, debe_continuar
            )

            for clave in stats_dia:
                estadisticas[clave] += stats_dia[clave]

            emitir(f"\n[RESUMEN] Resultados para {fecha_log}:")
            emitir(f"   - Fichas descargadas:        {stats_dia['detalles_exitosos']}")
            emitir(f"   - Omitidas (puntaje <= 0):   {stats_dia['detalles_omitidos']}")
            emitir(f"   - Errores/Pendientes:         {stats_dia['detalles_pendientes']}")

            if i < dias_totales - 1 and debe_continuar():
                emitir(f"\n[SISTEMA] Pausa de seguridad ({PAUSA_ENTRE_DIAS_EXTRACCION}s) antes del siguiente día...")
                time.sleep(PAUSA_ENTRE_DIAS_EXTRACCION)

        return estadisticas

    # =========================================================================
    # MÉTODOS PRIVADOS AUXILIARES
    # =========================================================================

    def _procesar_listado_diario(self, licitaciones: list, total_dia: int,
                                  emitir, debe_continuar) -> dict:
        """
        Procesa cada licitación de un día: evalúa, descarga detalle si aplica y persiste por lotes.
        """
        stats = {
            'detalles_exitosos': 0,
            'detalles_omitidos': 0,
            'detalles_pendientes': 0,
            'errores': 0
        }

        lote_licitaciones = []
        lote_organismos = []
        lote_estados = []
        
        # Sets de control para evitar duplicados dentro del mismo lote de inserción
        codigos_org_lote = set()
        codigos_est_lote = set()

        for idx, item in enumerate(licitaciones, 1):
            if not debe_continuar():
                break

            if idx % 20 == 0:
                emitir(f"   [AVANCE] Evaluando {idx}/{total_dia}...")

            datos_api, stats_item = self._procesar_item_individual(item, emitir)

            for clave in stats_item:
                stats[clave] += stats_item[clave]

            # TRANSFORMACIÓN Y PREPARACIÓN PARA PERSISTENCIA MASIVA
            fechas = TransformadorAPI.parsear_fechas(datos_api)
            texto_productos = TransformadorAPI.construir_texto_productos(datos_api)
            
            comprador = datos_api.get("Comprador", {})
            cod_org = comprador.get("CodigoOrganismo")
            cod_est = datos_api.get("CodigoEstado")

            registro_db = {
                "codigo_externo": datos_api.get("CodigoExterno"),
                "nombre": datos_api.get("Nombre"),
                "descripcion": datos_api.get("Descripcion"),
                "puntaje": datos_api.get("_PuntajeCalculado", 0),
                "justificacion_puntaje": datos_api.get("_Justificacion", ""),
                "etapa": datos_api.get("_EtapaAsignada", EtapaLicitacion.IGNORADA.value),
                "detalle_productos": texto_productos,
                "fecha_cierre": fechas["cierre"],
                "fecha_inicio": fechas["inicio"],
                "fecha_publicacion": fechas["publicacion"],
                "fecha_adjudicacion": fechas["adjudicacion"],
                "codigo_estado": cod_est,
                "codigo_organismo": cod_org,
                "tiene_detalle": datos_api.get("_TieneDetalle", False)
            }
            lote_licitaciones.append(registro_db)

            # Acumulación de entidades relacionadas para Bulk Insert
            if cod_org and cod_org not in codigos_org_lote:
                lote_organismos.append({
                    "codigo": cod_org, 
                    "nombre": comprador.get("NombreOrganismo", "Desconocido")
                })
                codigos_org_lote.add(cod_org)
                
            if cod_est and cod_est not in codigos_est_lote:
                lote_estados.append({
                    "codigo": cod_est, 
                    "descripcion": datos_api.get("Estado", "Desconocido")
                })
                codigos_est_lote.add(cod_est)

        # PERSISTENCIA VECTORIZADA: Se ejecuta una única transacción para todo el día
        try:
            if lote_licitaciones:
                emitir("   [BASE DE DATOS] Sincronizando lote diario con PostgreSQL...")
                self.almacenador.guardar_lote_masivo(lote_licitaciones, lote_organismos, lote_estados)
        except Exception as e:
            emitir(f"   [ERROR CRÍTICO] Fallo en persistencia masiva: {str(e)[:80]}")
            stats['errores'] += 1

        return stats

    def _procesar_item_individual(self, item: dict, emitir) -> tuple[dict, dict]:
        """
        Evalúa una licitación individual: aplica filtro de puntaje en título,
        y si supera el umbral, descarga y evalúa la ficha técnica completa.
        """
        stats = {'detalles_exitosos': 0, 'detalles_omitidos': 0,
                 'detalles_pendientes': 0, 'errores': 0}

        codigo_externo = item.get("CodigoExterno")
        titulo = item.get("Nombre", "")
        puntaje_inicial, motivos = self.calculadora.evaluar_titulo(titulo)

        datos_completos = item
        tiene_detalle = False
        puntaje_final = puntaje_inicial
        estado_descarga = "sin_intentar"
        etapa_asignada = EtapaLicitacion.IGNORADA.value

        if puntaje_inicial <= UMBRAL_PUNTAJE_CANDIDATA:
            # Filtro de primera capa: descartamos sin gastar peticiones de API
            stats['detalles_omitidos'] += 1
            estado_descarga = "omitido_puntaje_negativo"
        else:
            emitir(f"   [DESCARGA] {codigo_externo} (puntaje base: {puntaje_inicial})")
            resultado = self.recolector.obtener_detalle_licitacion(codigo_externo)
            detalle = resultado['datos']
            estado_api = resultado['estado']

            if detalle:
                datos_completos = detalle
                tiene_detalle = True
                stats['detalles_exitosos'] += 1
                estado_descarga = "exitoso"

                comprador = detalle.get("Comprador", {})
                cod_org = comprador.get("CodigoOrganismo", "")
                desc = detalle.get("Descripcion", "")
                items_str = self._extraer_texto_items(detalle)

                # EVALUACIÓN LÉXICA PURA
                puntaje_detalle, motivos_detalle = self.calculadora.evaluar_detalle(
                    desc, items_str
                )
                
                # INTEGRACIÓN DE PUNTAJE DESDE CACHÉ DE MEMORIA
                puntaje_org_cache = self.cache_organismos.get(cod_org, 0)
                
                puntaje_final = puntaje_inicial + puntaje_detalle + puntaje_org_cache
                motivos.extend(motivos_detalle)
                
                if puntaje_org_cache != 0:
                    motivos.append(f"[MATCH ORGANISMO] Puntaje institucional ({puntaje_org_cache:+d})")
                
                # Asignación de etapa utilizando Enums
                if puntaje_final > UMBRAL_PUNTAJE_CANDIDATA:
                    etapa_asignada = EtapaLicitacion.CANDIDATA.value 
                else:
                    etapa_asignada = EtapaLicitacion.IGNORADA.value

            else:
                if estado_api in ['error_servidor', 'error_red']:
                    stats['detalles_pendientes'] += 1
                    estado_descarga = f"pendiente_{estado_api}"
                elif estado_api == 'no_encontrado':
                    estado_descarga = "no_encontrado"
                else:
                    stats['errores'] += 1
                    estado_descarga = f"error_{estado_api}"

        datos_completos["_PuntajeCalculado"] = puntaje_final
        datos_completos["_TieneDetalle"] = tiene_detalle
        datos_completos["_EstadoDescarga"] = estado_descarga
        datos_completos["_Justificacion"] = "\n".join(motivos)
        datos_completos["_EtapaAsignada"] = etapa_asignada

        return datos_completos, stats

    def _extraer_texto_items(self, datos: dict) -> str:
        """
        Extrae y concatena los nombres y descripciones de los productos de la API
        en un único string para que la calculadora pueda evaluarlo con regex.
        """
        listado = datos.get("Items", {}).get("Listado", [])
        if not isinstance(listado, list):
            return ""
        return " ".join(
            f"{p.get('NombreProducto', '')} {p.get('Descripcion', '')}"
            for p in listado
        )