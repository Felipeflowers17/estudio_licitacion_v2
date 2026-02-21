import time
from datetime import timedelta

from src.scraper.recolector import RecolectorMercadoPublico
from src.services.almacenar import AlmacenadorLicitaciones
from src.repositories.licitaciones_repository import RepositorioLicitaciones
from src.services.instancias import calculadora_compartida
from src.utils.logger import configurar_logger
from src.config.constantes import PAUSA_ENTRE_DIAS_EXTRACCION, UMBRAL_PUNTAJE_CANDIDATA

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

            cod_org = datos_api.get("Comprador", {}).get("CodigoOrganismo", "")
            desc = datos_api.get("Descripcion", "")
            items_str = self._extraer_texto_items(datos_api)

            puntaje_detalle, motivos_detalle = self.calculadora.evaluar_detalle(
                cod_org, desc, items_str
            )

            datos_api["_PuntajeCalculado"] = puntaje_inicial + puntaje_detalle
            datos_api["_TieneDetalle"] = True
            datos_api["_EstadoDescarga"] = "exitoso_manual"
            datos_api["_Justificacion"] = "\n".join(motivos + motivos_detalle)
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
        Procesa cada licitación de un día: evalúa, descarga detalle si aplica y persiste.
        """
        stats = {
            'detalles_exitosos': 0,
            'detalles_omitidos': 0,
            'detalles_pendientes': 0,
            'errores': 0
        }

        for idx, item in enumerate(licitaciones, 1):
            if not debe_continuar():
                break

            if idx % 20 == 0:
                emitir(f"   [AVANCE] Procesando {idx}/{total_dia}...")

            datos_finales, stats_item = self._procesar_item_individual(item, emitir)

            for clave in stats_item:
                stats[clave] += stats_item[clave]

            try:
                self.almacenador.guardar_licitacion_individual(datos_finales)
            except Exception as e:
                emitir(f"   [ERROR BD] Fallo en persistencia: {str(e)[:80]}")
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
        etapa_asignada = "ignorada"

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

                cod_org = detalle.get("Comprador", {}).get("CodigoOrganismo", "")
                desc = detalle.get("Descripcion", "")
                items_str = self._extraer_texto_items(detalle)

                puntaje_detalle, motivos_detalle = self.calculadora.evaluar_detalle(
                    cod_org, desc, items_str
                )
                puntaje_final = puntaje_inicial + puntaje_detalle
                motivos.extend(motivos_detalle)
                etapa_asignada = "candidata" if puntaje_final > UMBRAL_PUNTAJE_CANDIDATA else "ignorada"

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