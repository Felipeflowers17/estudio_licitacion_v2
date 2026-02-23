from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel, 
                               QTextEdit, QGroupBox, QScrollArea, QWidget)
from PySide6.QtCore import Qt

class DialogoDetalleLicitacion(QDialog):
    """
    Ventana emergente que muestra el detalle completo y profundo de una licitación,
    incluyendo su justificación de puntaje y el listado de productos requeridos.
    Actúa estrictamente como una Vista pasiva: recibe los datos y los renderiza.
    """
    
    def __init__(self, licitacion_data, parent=None):
        super().__init__(parent)
        
        # Inyección de dependencias: la vista ya no busca los datos, los recibe.
        self.licitacion = licitacion_data
        
        if not self.licitacion:
            self.setWindowTitle("Ficha Técnica - Error")
            self.resize(400, 200)
            self.layout_principal = QVBoxLayout(self)
            self.layout_principal.addWidget(QLabel("[ERROR] No se recibieron datos para esta licitación."))
            return

        self.setWindowTitle(f"Ficha Técnica de Licitación: {self.licitacion.codigo_externo}")
        self.resize(850, 800)
        
        self.layout_principal = QVBoxLayout(self)
        
        area_desplazable = QScrollArea()
        area_desplazable.setWidgetResizable(True)
        widget_contenido = QWidget()
        self.layout_contenido = QVBoxLayout(widget_contenido)
        
        # 1. Título principal
        etiqueta_titulo = QLabel(self.licitacion.nombre)
        etiqueta_titulo.setWordWrap(True)
        etiqueta_titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #005a9e; margin: 10px 0;")
        self.layout_contenido.addWidget(etiqueta_titulo)
        
        # 2. Panel de datos generales
        self.crear_panel_informacion()
        
        # 3. Listado de productos
        self.crear_bloque_texto("Productos e Ítems Requeridos", self.licitacion.detalle_productos, "#fff3e0")

        # 4. Descripción técnica del comprador
        self.crear_bloque_texto("Descripción Técnica", self.licitacion.descripcion)
        
        # 5. Auditoría del puntaje
        self.crear_bloque_texto("Análisis de Evaluación (Auditoría de Puntaje)", self.licitacion.justificacion_puntaje, "#e8f5e9")

        self.layout_contenido.addStretch()
        area_desplazable.setWidget(widget_contenido)
        self.layout_principal.addWidget(area_desplazable)

    def crear_panel_informacion(self):
        """Construye el formulario superior con datos clave como fechas, estado y organismo."""
        grupo = QGroupBox("Información Institucional y Plazos")
        formulario = QFormLayout(grupo)
        
        nombre_organismo = self.licitacion.organismo.nombre if self.licitacion.organismo else "No registrado"
        formulario.addRow("Organismo Comprador:", QLabel(nombre_organismo))
        
        descripcion_estado = self.licitacion.estado.descripcion if self.licitacion.estado else str(self.licitacion.codigo_estado)
        formulario.addRow("Estado Actual:", QLabel(descripcion_estado))
        
        # Función auxiliar para formatear fechas de manera segura
        def formatear_fecha(fecha): return fecha.strftime("%d-%m-%Y %H:%M") if fecha else "Dato no disponible"
        
        formulario.addRow("Fecha de Publicación:", QLabel(formatear_fecha(self.licitacion.fecha_publicacion)))
        formulario.addRow("Cierre de Recepción de Ofertas:", QLabel(formatear_fecha(self.licitacion.fecha_cierre)))
        formulario.addRow("Fecha Estimada de Adjudicación:", QLabel(formatear_fecha(self.licitacion.fecha_adjudicacion)))
        
        self.layout_contenido.addWidget(grupo)

    def crear_bloque_texto(self, titulo_bloque: str, contenido_texto: str, color_fondo: str = "#ffffff"):
        """Instancia un área de texto de solo lectura para mostrar información extensa."""
        if not contenido_texto: 
            contenido_texto = "Sin información registrada en el sistema."
            
        grupo = QGroupBox(titulo_bloque)
        layout_grupo = QVBoxLayout(grupo)
        
        caja_texto = QTextEdit()
        caja_texto.setPlainText(contenido_texto)
        caja_texto.setReadOnly(True)
        caja_texto.setStyleSheet(f"background-color: {color_fondo}; border: 1px solid #ddd;")
        caja_texto.setFixedHeight(120)
        
        layout_grupo.addWidget(caja_texto)
        self.layout_contenido.addWidget(grupo)