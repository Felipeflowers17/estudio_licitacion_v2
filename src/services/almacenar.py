from datetime import datetime
from sqlalchemy.orm import Session
from src.bd.database import SessionLocal
from src.bd.models import Licitacion, EstadoLicitacion, Organismo
from src.utils.logger import configurar_logger

logger = configurar_logger("almacenador_bd")


class AlmacenadorLicitaciones:
    """
    Gestiona la inserción y actualización (Upsert) de los datos crudos 
    provenientes de la API hacia nuestra base de datos relacional.
    
    Cada responsabilidad está aislada en un método privado para facilitar
    el mantenimiento, la depuración y las pruebas unitarias independientes.
    """

    def __init__(self, session_factory=SessionLocal):
        """
        Inicializa el almacenador mediante inyección de dependencias.
        Crucial para aislar transacciones durante las pruebas del scraper.
        """
        self.session_factory = session_factory

    # =========================================================================
    # MÉTODO PÚBLICO PRINCIPAL
    # =========================================================================

    def guardar_licitacion_individual(self, datos_licitacion: dict):
        """
        Orquesta el proceso completo de persistencia de una licitación.
        
        Delega cada etapa a métodos privados especializados y ejecuta
        un único commit al final para garantizar la atomicidad de la transacción.
        Si cualquier paso falla, el rollback revierte todos los cambios.
        """
        codigo_externo = datos_licitacion.get("CodigoExterno")
        if not codigo_externo:
            logger.warning("Intento de guardar licitación sin código externo. Operación abortada.")
            return

        with self.session_factory() as sesion:
            try:
                # 1. Garantizar existencia de entidades relacionadas
                datos_comprador = datos_licitacion.get("Comprador", {})
                self._asegurar_organismo(sesion, datos_comprador)

                codigo_estado = datos_licitacion.get("CodigoEstado")
                descripcion_estado = datos_licitacion.get("Estado", "Desconocido")
                self._asegurar_estado(sesion, codigo_estado, descripcion_estado)

                # 2. Transformar datos crudos en valores listos para persistir
                fechas = self._parsear_fechas(datos_licitacion)
                texto_productos = self._construir_texto_productos(datos_licitacion)

                # 3. Extraer metadatos calculados por el orquestador
                metadatos = self._extraer_metadatos(datos_licitacion)

                # 4. Ejecutar el UPSERT sobre el registro de licitación
                self._upsert_licitacion(
                    sesion=sesion,
                    codigo_externo=codigo_externo,
                    datos_licitacion=datos_licitacion,
                    datos_comprador=datos_comprador,
                    fechas=fechas,
                    texto_productos=texto_productos,
                    metadatos=metadatos
                )

                # 5. Confirmar toda la transacción en un único commit atómico
                sesion.commit()

            except Exception as error_bd:
                # Rollback obligatorio para no dejar la sesión en estado corrupto
                sesion.rollback()
                logger.error(f"Error guardando licitación {codigo_externo}: {error_bd}")

    # =========================================================================
    # MÉTODOS PRIVADOS DE TRANSFORMACIÓN (Sin acceso a BD, 100% testeables)
    # =========================================================================

    def _parsear_fechas(self, datos: dict) -> dict:
        """
        Extrae y convierte todas las fechas del diccionario crudo de la API
        desde formato ISO string hacia objetos datetime de Python.
        
        Retorna un diccionario con claves estandarizadas, con None
        si la fecha no existe o no puede ser parseada.
        """
        objeto_fechas = datos.get("Fechas", {})

        def _convertir(texto_fecha: str):
            """Convierte un string ISO a datetime, retornando None si falla."""
            if not texto_fecha:
                return None
            try:
                return datetime.strptime(texto_fecha, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                logger.warning(f"Formato de fecha no reconocido: '{texto_fecha}'")
                return None

        return {
            "cierre": _convertir(
                datos.get("FechaCierre") or objeto_fechas.get("FechaCierre")
            ),
            "inicio": _convertir(objeto_fechas.get("FechaInicio")),
            "publicacion": _convertir(objeto_fechas.get("FechaPublicacion")),
            "adjudicacion": (
                _convertir(objeto_fechas.get("FechaAdjudicacion"))
                or _convertir(objeto_fechas.get("FechaEstimadaAdjudicacion"))
            ),
        }

    def _construir_texto_productos(self, datos: dict) -> str:
        """
        Transforma el listado de ítems de la API en un texto formateado
        y legible para su almacenamiento y posterior visualización.
        
        Retorna un string vacío si no hay productos en los datos.
        """
        objeto_items = datos.get("Items", {})

        # La API puede retornar Items como dict con "Listado" o directamente como lista
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

            # Solo añadimos la descripción si aporta información adicional al nombre
            if descripcion and descripcion.lower() != nombre.lower():
                lineas.append(f"  Detalle: {descripcion}")

        return "\n".join(lineas)

    def _extraer_metadatos(self, datos: dict) -> dict:
        """
        Centraliza la extracción de las claves privadas (_) que el orquestador
        inyecta en el diccionario para comunicar resultados del análisis.
        
        Usar este método evita que las claves mágicas estén dispersas por el código.
        """
        return {
            "puntaje": datos.get("_PuntajeCalculado", 0),
            "tiene_detalle": datos.get("_TieneDetalle", False),
            "justificacion": datos.get("_Justificacion", ""),
            "etapa": datos.get("_EtapaAsignada", "ignorada"),
        }

    # =========================================================================
    # MÉTODOS PRIVADOS DE PERSISTENCIA (Requieren sesión activa de BD)
    # =========================================================================

    def _asegurar_organismo(self, sesion: Session, datos_comprador: dict):
        """
        Verifica si el organismo comprador existe en la BD y lo crea si no.
        Usa flush() para obtener el ID sin consolidar la transacción completa,
        permitiendo que el commit final sea el único punto de verdad.
        """
        codigo = datos_comprador.get("CodigoOrganismo")
        if not codigo:
            return

        existe = sesion.query(Organismo).filter_by(codigo=codigo).first()
        if not existe:
            nombre = datos_comprador.get("NombreOrganismo", "Organismo Desconocido")
            sesion.add(Organismo(codigo=codigo, nombre=nombre))
            sesion.flush()
            logger.info(f"Nuevo organismo registrado: {nombre} ({codigo})")

    def _asegurar_estado(self, sesion: Session, codigo: int, descripcion: str):
        """
        Verifica si el estado de licitación existe en la BD y lo crea si no.
        Mismo patrón que _asegurar_organismo para mantener consistencia.
        """
        if codigo is None:
            return

        existe = sesion.query(EstadoLicitacion).filter_by(codigo=codigo).first()
        if not existe:
            sesion.add(EstadoLicitacion(codigo=codigo, descripcion=descripcion))
            sesion.flush()
            logger.info(f"Nuevo estado registrado: {descripcion} (código {codigo})")

    def _upsert_licitacion(self, sesion: Session, codigo_externo: str,
                           datos_licitacion: dict, datos_comprador: dict,
                           fechas: dict, texto_productos: str, metadatos: dict):
        """
        Ejecuta la operación UPSERT: actualiza el registro si ya existe,
        o inserta uno nuevo si es la primera vez que se ve este código.
        
        La lógica de ascenso de etapa ('ignorada' → 'candidata') también
        reside aquí para centralizar todas las reglas de negocio del UPSERT.
        """
        registro_existente = sesion.query(Licitacion).filter_by(
            codigo_externo=codigo_externo
        ).first()

        if registro_existente:
            self._actualizar_registro(
                registro_existente, datos_licitacion, datos_comprador,
                fechas, texto_productos, metadatos
            )
        else:
            nuevo_registro = self._crear_registro(
                codigo_externo, datos_licitacion, datos_comprador,
                fechas, texto_productos, metadatos
            )
            sesion.add(nuevo_registro)

    def _actualizar_registro(self, registro: Licitacion, datos: dict,
                              datos_comprador: dict, fechas: dict,
                              texto_productos: str, metadatos: dict):
        """
        Aplica las actualizaciones sobre un registro de licitación existente.
        
        Regla de negocio: Los campos de detalle (descripción, productos, organismo)
        solo se sobreescriben si la descarga actual trajo datos completos.
        Regla de ascenso: Una licitación 'ignorada' asciende a 'candidata' si
        al ser reevaluada obtiene un puntaje positivo.
        """
        # Campos que siempre se actualizan (datos del listado básico)
        registro.nombre = datos.get("Nombre") or registro.nombre
        registro.codigo_estado = datos.get("CodigoEstado")
        registro.fecha_cierre = fechas["cierre"] or registro.fecha_cierre
        registro.fecha_inicio = fechas["inicio"]
        registro.fecha_publicacion = fechas["publicacion"]
        registro.fecha_adjudicacion = fechas["adjudicacion"]
        registro.puntaje = metadatos["puntaje"]
        registro.justificacion_puntaje = metadatos["justificacion"]

        # Campos de detalle: solo se actualizan si se descargó la ficha completa
        if metadatos["tiene_detalle"]:
            registro.codigo_organismo = datos_comprador.get("CodigoOrganismo")
            registro.descripcion = datos.get("Descripcion")
            registro.detalle_productos = texto_productos
            registro.tiene_detalle = True

        # Regla de ascenso de etapa (nunca retrocede una etapa manualmente asignada)
        if registro.etapa == "ignorada" and metadatos["etapa"] == "candidata":
            registro.etapa = "candidata"

    def _crear_registro(self, codigo_externo: str, datos: dict,
                         datos_comprador: dict, fechas: dict,
                         texto_productos: str, metadatos: dict) -> Licitacion:
        """
        Construye y retorna una nueva instancia de Licitacion lista para ser
        añadida a la sesión. No ejecuta ninguna operación de BD directamente.
        """
        return Licitacion(
            codigo_externo=codigo_externo,
            nombre=datos.get("Nombre"),
            codigo_estado=datos.get("CodigoEstado"),
            descripcion=datos.get("Descripcion"),
            codigo_organismo=datos_comprador.get("CodigoOrganismo"),
            tiene_detalle=metadatos["tiene_detalle"],
            puntaje=metadatos["puntaje"],
            justificacion_puntaje=metadatos["justificacion"],
            etapa=metadatos["etapa"],
            detalle_productos=texto_productos,
            fecha_cierre=fechas["cierre"],
            fecha_inicio=fechas["inicio"],
            fecha_publicacion=fechas["publicacion"],
            fecha_adjudicacion=fechas["adjudicacion"],
        )