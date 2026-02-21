from src.scraper.recolector import RecolectorMercadoPublico
from src.repositories.almacenar import AlmacenadorLicitaciones
from src.services.calculadora import CalculadoraPuntajes
from src.repositories.licitaciones_repository import RepositorioLicitaciones
from src.utils.logger import configurar_logger
import time
from datetime import timedelta

logger = configurar_logger("orquestador_ingesta")

class OrquestadorIngesta:
    """
    Servicio de aplicación encargado de coordinar el flujo completo de 
    extracción, evaluación y persistencia de licitaciones.
    Implementa el patrón Facade para ocultar la complejidad a la interfaz gráfica.
    """
    def __init__(self):
        self.recolector = RecolectorMercadoPublico()
        self.almacenador = AlmacenadorLicitaciones()
        self.calculadora = CalculadoraPuntajes()
        self.repositorio_licitaciones = RepositorioLicitaciones()

    def procesar_licitacion_manual(self, codigo: str, etapa_destino: str, callback_progreso=None) -> tuple[bool, str]:
        """
        Descarga, evalúa y almacena una licitación específica.
        Utiliza inyección de un callback opcional para reportar progreso 
        sin acoplarse a librerías de interfaz gráfica (PySide6).
        """
        def emitir(mensaje):
            if callback_progreso:
                callback_progreso(mensaje)

        try:
            emitir("Consultando API de Mercado Público...")
            resultado = self.recolector.obtener_detalle_licitacion(codigo)

            if resultado['estado'] != 'exitoso' or not resultado.get('datos'):
                return False, f"No fue posible encontrar la licitación {codigo}. Estado: {resultado['estado']}"

            datos_api = resultado['datos']

            emitir("Evaluando reglas de negocio...")
            titulo = datos_api.get("Nombre", "")
            puntaje_inicial, motivos = self.calculadora.evaluar_titulo(titulo)

            cod_org = datos_api.get("Comprador", {}).get("CodigoOrganismo", "")
            desc = datos_api.get("Descripcion", "")

            items_str = ""
            if "Items" in datos_api and "Listado" in datos_api["Items"]:
                for prod in datos_api["Items"]["Listado"]:
                    items_str += f"{prod.get('NombreProducto', '')} {prod.get('Descripcion', '')} "

            puntaje_detalle, motivos_detalle = self.calculadora.evaluar_detalle(cod_org, desc, items_str)
            
            # Inyección de metadatos procesados
            datos_api["_PuntajeCalculado"] = puntaje_inicial + puntaje_detalle
            datos_api["_TieneDetalle"] = True
            datos_api["_EstadoDescarga"] = "exitoso_manual"
            motivos.extend(motivos_detalle)
            datos_api["_Justificacion"] = "\n".join(motivos)
            datos_api["_EtapaAsignada"] = etapa_destino 

            emitir("Guardando en base de datos...")
            self.almacenador.guardar_licitacion_individual(datos_api)
            
            self.repositorio_licitaciones.mover_licitacion(codigo, etapa_destino)

            return True, f"La licitación {codigo} fue procesada exitosamente."

        except Exception as e:
            logger.error(f"Error en orquestador manual para {codigo}: {e}")
            return False, f"Ocurrió un error inesperado: {str(e)}"
        
    def procesar_rango_fechas(self, fecha_inicio, fecha_fin, callback_progreso=None, verificador_ejecucion=None) -> dict:
        """
        Orquesta la descarga masiva de licitaciones en un rango de fechas.
        Delega el procesamiento de cada día a un método privado.
        """
        def emitir(mensaje):
            if callback_progreso: callback_progreso(mensaje)

        def debe_continuar():
            if verificador_ejecucion: return verificador_ejecucion()
            return True

        estadisticas = {
            'licitaciones_basicas': 0, 'detalles_exitosos': 0,
            'detalles_pendientes': 0, 'detalles_omitidos': 0, 'errores': 0
        }

        delta_tiempo = fecha_fin - fecha_inicio
        dias_totales = delta_tiempo.days + 1

        emitir(f"[INFO] Iniciando proceso asíncrono para {dias_totales} días.")

        for i in range(dias_totales):
            if not debe_continuar():
                emitir("[WARNING] Proceso interrumpido por el usuario.")
                break

            fecha_actual = fecha_inicio + timedelta(days=i)
            str_fecha = fecha_actual.strftime("%d%m%Y")
            fecha_log = fecha_actual.strftime("%d-%m-%Y")

            emitir(f"\n{'='*60}\n[PROCESANDO] Día {i+1}/{dias_totales} - Fecha: {fecha_log}\n{'='*60}")
            emitir("[RECOGIDA] Solicitando listado principal...")

            licitaciones_basicas = self.recolector.obtener_licitaciones_diarias(fecha_cadena=str_fecha)

            if not licitaciones_basicas:
                emitir(f"[INFO] No se registraron licitaciones para la fecha {fecha_log}.")
                continue

            total_dia = len(licitaciones_basicas)
            estadisticas['licitaciones_basicas'] += total_dia
            emitir(f"[INFO] Total detectado: {total_dia}. Iniciando filtrado de primera capa.")

            estadisticas_dia = self._procesar_listado_diario(
                licitaciones_basicas, total_dia, emitir, debe_continuar
            )

            # Acumular estadísticas globales
            for clave in estadisticas_dia:
                estadisticas[clave] += estadisticas_dia[clave]

            emitir(f"\n[RESUMEN] Resultados para {fecha_log}:")
            emitir(f"   - Fichas técnicas descargadas: {estadisticas_dia['detalles_exitosos']}")
            emitir(f"   - Omitidas (Filtro negativo): {estadisticas_dia['detalles_omitidos']}")
            emitir(f"   - Errores/Pendientes: {estadisticas_dia['detalles_pendientes']}")

            if i < dias_totales - 1 and debe_continuar():
                emitir("\n[SISTEMA] Pausa de seguridad (5s) antes del siguiente día de extracción...")
                time.sleep(5)

        return estadisticas

    def _procesar_listado_diario(self, licitaciones: list, total_dia: int, emitir, debe_continuar) -> dict:
        """
        Método privado que aísla la lógica de procesamiento de una sola jornada.
        Mejora la legibilidad y permite pruebas unitarias independientes.
        """
        stats = {'detalles_exitosos': 0, 'detalles_omitidos': 0, 'detalles_pendientes': 0, 'errores': 0}

        for idx, item in enumerate(licitaciones, 1):
            if not debe_continuar(): break

            if idx % 20 == 0: 
                emitir(f"   [AVANCE] Analizando elemento {idx} de {total_dia}...")

            codigo_externo = item.get("CodigoExterno")
            titulo = item.get("Nombre", "")
            puntaje_inicial, motivos_totales = self.calculadora.evaluar_titulo(titulo)

            datos_completos = item
            tiene_detalle = False
            puntaje_final = puntaje_inicial
            estado_descarga = "sin_intentar"
            etapa_asignada = "ignorada"

            if puntaje_inicial <= 0:
                stats['detalles_omitidos'] += 1
                estado_descarga = "omitido_puntaje_negativo"
            else:
                emitir(f"   [DESCARGA] Código: {codigo_externo} (Puntaje base: {puntaje_inicial})")
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
                    items_str = "".join([f"{p.get('NombreProducto','')} {p.get('Descripcion','')}" for p in detalle.get("Items", {}).get("Listado", [])])

                    puntaje_detalle, motivos_detalle = self.calculadora.evaluar_detalle(cod_org, desc, items_str)
                    puntaje_final = puntaje_inicial + puntaje_detalle
                    motivos_totales.extend(motivos_detalle)
                    etapa_asignada = "candidata" if puntaje_final > 0 else "ignorada"
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
            datos_completos["_Justificacion"] = "\n".join(motivos_totales)
            datos_completos["_EtapaAsignada"] = etapa_asignada

            try:
                self.almacenador.guardar_licitacion_individual(datos_completos)
            except Exception as e:
                emitir(f"   [ERROR BD] Fallo en persistencia: {str(e)[:50]}")
                stats['errores'] += 1

        return stats