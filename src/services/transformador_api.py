from datetime import datetime
from src.utils.logger import configurar_logger

logger = configurar_logger("transformador_api")

class TransformadorAPI:
    """
    Servicio utilitario estático encargado exclusivamente de limpiar, parsear 
    y transformar los diccionarios crudos de la API de Mercado Público 
    a tipos de datos nativos de Python.
    """

    @staticmethod
    def parsear_fechas(datos: dict) -> dict:
        """Extrae y convierte fechas desde formato ISO string a datetime."""
        objeto_fechas = datos.get("Fechas", {})

        def _convertir(texto_fecha: str):
            if not texto_fecha:
                return None
            try:
                texto_limpio = texto_fecha.replace("Z", "+00:00")
                return datetime.fromisoformat(texto_limpio)
            except ValueError:
                logger.warning(f"Formato de fecha no reconocido: '{texto_fecha}'")
                return None

        return {
            "cierre": _convertir(datos.get("FechaCierre") or objeto_fechas.get("FechaCierre")),
            "inicio": _convertir(objeto_fechas.get("FechaInicio")),
            "publicacion": _convertir(objeto_fechas.get("FechaPublicacion")),
            "adjudicacion": (
                _convertir(objeto_fechas.get("FechaAdjudicacion"))
                or _convertir(objeto_fechas.get("FechaEstimadaAdjudicacion"))
            ),
        }

    @staticmethod
    def construir_texto_productos(datos: dict) -> str:
        """Transforma el listado de ítems en un texto estructurado."""
        objeto_items = datos.get("Items", {})

        if isinstance(objeto_items, dict):
            lista_productos = objeto_items.get("Listado", [])
        elif isinstance(objeto_items, list):
            lista_productos = objeto_items
        else:
            return ""

        lineas = []
        for producto in lista_productos:
            nombre = producto.get("NombreProducto", "Producto genérico")
            cantidad = producto.get("Cantidad", 0)
            unidad = producto.get("UnidadMedida", "un")
            descripcion = producto.get("Descripcion", "")

            lineas.append(f"- {nombre} ({cantidad} {unidad})")
            if descripcion and descripcion.lower() != nombre.lower():
                lineas.append(f"  Detalle: {descripcion}")

        return "\n".join(lineas)