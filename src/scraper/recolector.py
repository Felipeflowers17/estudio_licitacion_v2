import os
import time
from datetime import datetime
import requests
from src.utils.logger import configurar_logger

logger = configurar_logger("recolector_api")

class RecolectorMercadoPublico:
    """
    Clase encargada de interactuar con la API de Mercado Público.
    Implementa mecanismos de resiliencia como pausas controladas y 
    reintentos exponenciales para evitar bloqueos por exceso de peticiones.
    """

    def __init__(self):
        self.ticket = os.getenv("TICKET_MERCADO_PUBLICO")
        self.url_base = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
        
        # Configuración de límites de tasa (Rate Limiting)
        self.min_pausa_entre_peticiones = 2.0
        self.ultima_peticion = 0.0
        
        # Configuración de resiliencia (Backoff)
        self.max_intentos = 4
        self.base_retraso = 1.5

        if not self.ticket:
            logger.error("[CRITICAL] TICKET_MERCADO_PUBLICO no está configurado.")
            raise ValueError("El ticket de la API es requerido para inicializar el recolector.")
    
    def _esperar_limite_tasa(self):
        """Bloquea la ejecución temporalmente para respetar los límites de la API."""
        ahora = time.time()
        tiempo_transcurrido = ahora - self.ultima_peticion
        
        if tiempo_transcurrido < self.min_pausa_entre_peticiones:
            pausa_necesaria = self.min_pausa_entre_peticiones - tiempo_transcurrido
            time.sleep(pausa_necesaria)
            
        self.ultima_peticion = time.time()
    
    def obtener_licitaciones_diarias(self, fecha_cadena: str = None) -> list:
        """
        Descarga el listado general de licitaciones publicadas en una fecha específica.
        """
        if not fecha_cadena:
            fecha_cadena = datetime.now().strftime("%d%m%Y")
        
        parametros = {
            "ticket": self.ticket,
            "fecha": fecha_cadena,
            "estado": "activas"
        }

        logger.info(f"Iniciando recolección de licitaciones para la fecha: {fecha_cadena}")
        self._esperar_limite_tasa()

        try:
            respuesta = requests.get(self.url_base, params=parametros, timeout=15)
            respuesta.raise_for_status()
            datos = respuesta.json()

            if "Listado" in datos: 
                cantidad = datos.get("Cantidad", 0)
                logger.info(f"Recolección exitosa. Licitaciones encontradas: {cantidad}")
                return datos["Listado"]
            else:
                logger.warning("La respuesta de la API no contiene el nodo 'Listado'.")
                return []
                
        except requests.RequestException as error_red:
            logger.error(f"Error de red al obtener listado diario: {error_red}")
            return []
        
    def obtener_detalle_licitacion(self, codigo_externo: str) -> dict:
        """
        Descarga la ficha técnica completa de una licitación específica.
        Retorna un diccionario con los datos y el estado final de la descarga.
        """
        if not codigo_externo:
            return {'datos': None, 'estado': 'error_entrada'}
        
        cabeceras = {
            "User-Agent": "MonitorCA/1.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json"
        }
        
        parametros = {
            "codigo": codigo_externo,
            "ticket": self.ticket
        }
        
        for intento in range(self.max_intentos):
            try:
                self._esperar_limite_tasa()
                respuesta = requests.get(self.url_base, params=parametros, headers=cabeceras, timeout=15)
                
                if respuesta.status_code == 200:
                    datos = respuesta.json()
                    if "Listado" in datos and len(datos["Listado"]) > 0:
                        return {'datos': datos["Listado"][0], 'estado': 'exitoso'}
                    return {'datos': None, 'estado': 'no_encontrado'}
                
                elif respuesta.status_code == 404:
                    return {'datos': None, 'estado': 'no_encontrado'}
                
                elif 500 <= respuesta.status_code < 600:
                    if intento < self.max_intentos - 1:
                        import random
                        tiempo_espera = (self.base_retraso ** (intento + 1)) + random.uniform(0, 2)
                        logger.warning(f"Error servidor {respuesta.status_code}. Reintento {intento+1} en {tiempo_espera:.1f}s")
                        time.sleep(tiempo_espera)
                        continue
                    return {'datos': None, 'estado': 'error_servidor'}
                
                else:
                    return {'datos': None, 'estado': 'error_cliente'}
                    
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if intento < self.max_intentos - 1:
                    time.sleep(self.base_retraso ** intento)
                    continue
                return {'datos': None, 'estado': 'error_red'}
            except Exception as e:
                logger.error(f"Error crítico no controlado al descargar detalle: {e}")
                return {'datos': None, 'estado': 'error_critico'}
        
        return {'datos': None, 'estado': 'error_agotado'}