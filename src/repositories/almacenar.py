from datetime import datetime
from src.bd.database import SessionLocal
from src.bd.models import Licitacion, EstadoLicitacion, Organismo
from src.utils.logger import configurar_logger

logger = configurar_logger("almacenador_bd")

class AlmacenadorLicitaciones:
    """
    Gestiona la inserción y actualización (Upsert) de los datos crudos 
    provenientes de la API hacia nuestra base de datos relacional.
    """
    
    def __init__(self, session_factory=SessionLocal):
        """
        Inicializa el almacenador mediante inyección de dependencias.
        Crucial para aislar transacciones durante las futuras pruebas del scraper.
        """
        self.session_factory = session_factory

    def guardar_licitacion_individual(self, datos_licitacion: dict):
        """
        Procesa un diccionario con los datos de la API y lo persiste en la BD.
        Actualiza los registros si la licitación ya existía previamente.
        """
        with self.session_factory() as sesion:
            try:
                # --- 1. Extracción de datos fundamentales ---
                codigo_externo = datos_licitacion.get("CodigoExterno")
                if not codigo_externo:
                    logger.warning("Intento de guardar licitación sin código externo. Operación abortada.")
                    return
                
                nombre_licitacion = datos_licitacion.get("Nombre")
                codigo_estado = datos_licitacion.get("CodigoEstado")
                descripcion_estado = datos_licitacion.get("Estado", "Desconocido")
                
                # --- 2. Extracción de datos de comprador y descripción ---
                datos_comprador = datos_licitacion.get("Comprador", {})
                codigo_organismo = datos_comprador.get("CodigoOrganismo")
                descripcion_tecnica = datos_licitacion.get("Descripcion")
                
                # --- 3. Extracción de metadatos del Worker ---
                puntaje_calculado = datos_licitacion.get("_PuntajeCalculado", 0)
                bandera_detalle = datos_licitacion.get("_TieneDetalle", False)
                justificacion_texto = datos_licitacion.get("_Justificacion", "") 
                etapa_asignada = datos_licitacion.get("_EtapaAsignada", "ignorada") 

                # --- 4. Procesamiento de Fechas ---
                objeto_fechas = datos_licitacion.get("Fechas", {})
                
                def parsear_fecha(texto_fecha: str):
                    if not texto_fecha: return None
                    try:
                        return datetime.strptime(texto_fecha, "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        return None

                fecha_cierre = parsear_fecha(datos_licitacion.get("FechaCierre") or objeto_fechas.get("FechaCierre"))
                fecha_inicio = parsear_fecha(objeto_fechas.get("FechaInicio"))
                fecha_publicacion = parsear_fecha(objeto_fechas.get("FechaPublicacion"))
                fecha_adjudicacion = parsear_fecha(objeto_fechas.get("FechaAdjudicacion")) or parsear_fecha(objeto_fechas.get("FechaEstimadaAdjudicacion"))

                # --- 5. Procesamiento de Productos ---
                texto_productos = ""
                objeto_items = datos_licitacion.get("Items", {})
                lista_productos = []
                
                if isinstance(objeto_items, dict) and "Listado" in objeto_items:
                    lista_productos = objeto_items["Listado"]
                elif isinstance(objeto_items, list):
                    lista_productos = objeto_items

                for producto in lista_productos:
                    nombre_prod = producto.get("NombreProducto", "Producto genérico")
                    cantidad_prod = producto.get("Cantidad", 0)
                    unidad_prod = producto.get("UnidadMedida", "un")
                    desc_prod = producto.get("Descripcion", "")
                    
                    texto_productos += f"- {nombre_prod} ({cantidad_prod} {unidad_prod})\n"
                    if desc_prod and desc_prod.lower() != nombre_prod.lower():
                        texto_productos += f"  Detalle: {desc_prod}\n"

                # --- 6. Persistencia de Entidades Relacionadas (Organismo y Estado) ---
                if codigo_organismo:
                    nombre_org = datos_comprador.get("NombreOrganismo", "Organismo Desconocido")
                    organismo_bd = sesion.query(Organismo).filter_by(codigo=codigo_organismo).first()
                    if not organismo_bd:
                        nuevo_organismo = Organismo(codigo=codigo_organismo, nombre=nombre_org)
                        sesion.add(nuevo_organismo)
                        # Nota técnica: Usamos flush en lugar de commit. Flush envía el SQL a la BD 
                        # para obtener IDs generados sin consolidar la transacción completa.
                        sesion.flush()

                estado_bd = sesion.query(EstadoLicitacion).filter_by(codigo=codigo_estado).first()
                if not estado_bd:
                    nuevo_estado = EstadoLicitacion(codigo=codigo_estado, descripcion=descripcion_estado)
                    sesion.add(nuevo_estado)
                    sesion.flush()

                # --- 7. Operación UPSERT en Licitación ---
                registro_existente = sesion.query(Licitacion).filter_by(codigo_externo=codigo_externo).first()
                
                if registro_existente:
                    registro_existente.nombre = nombre_licitacion or registro_existente.nombre
                    registro_existente.codigo_estado = codigo_estado
                    registro_existente.fecha_cierre = fecha_cierre or registro_existente.fecha_cierre
                    registro_existente.fecha_inicio = fecha_inicio
                    registro_existente.fecha_publicacion = fecha_publicacion
                    registro_existente.fecha_adjudicacion = fecha_adjudicacion
                    
                    if bandera_detalle:
                        registro_existente.codigo_organismo = codigo_organismo
                        registro_existente.descripcion = descripcion_tecnica
                        registro_existente.detalle_productos = texto_productos
                        registro_existente.tiene_detalle = True
                    
                    registro_existente.puntaje = puntaje_calculado
                    registro_existente.justificacion_puntaje = justificacion_texto
                    
                    # Si estaba ignorada y ahora califica, la ascendemos
                    if registro_existente.etapa == "ignorada" and etapa_asignada == "candidata":
                        registro_existente.etapa = "candidata"
                    
                else:
                    nueva_licitacion = Licitacion(
                        codigo_externo=codigo_externo,
                        nombre=nombre_licitacion,
                        codigo_estado=codigo_estado,
                        descripcion=descripcion_tecnica,
                        tiene_detalle=bandera_detalle,
                        puntaje=puntaje_calculado,
                        justificacion_puntaje=justificacion_texto,
                        codigo_organismo=codigo_organismo,
                        fecha_cierre=fecha_cierre,
                        fecha_inicio=fecha_inicio,
                        fecha_publicacion=fecha_publicacion,
                        fecha_adjudicacion=fecha_adjudicacion,
                        detalle_productos=texto_productos,
                        etapa=etapa_asignada 
                    )
                    sesion.add(nueva_licitacion)
                
                # Consolidamos toda la transacción (Organismos, Estados y Licitación) a la vez
                sesion.commit()
                
            except Exception as error_bd:
                # Es mandatorio hacer rollback si capturamos el error para no dejar 
                # la sesión en un estado colapsado.
                sesion.rollback()
                logger.error(f"Error guardando licitación {datos_licitacion.get('CodigoExterno')}: {error_bd}")