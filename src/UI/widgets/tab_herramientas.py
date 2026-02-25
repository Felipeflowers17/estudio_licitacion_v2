from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QLabel)
from PySide6.QtCore import Signal

# Importaciones de subpestañas (Ajustadas al estándar de nomenclatura que aplicaremos)
from src.UI.widgets.sub_tabs_herramientas.tab_extraer import SubTabExtraer
from src.UI.widgets.sub_tabs_herramientas.tab_exportar import SubTabExportar
from src.UI.widgets.sub_tabs_herramientas.tab_puntajes import SubTabPuntajes
from src.UI.widgets.sub_tabs_herramientas.tab_piloto_automatico import SubTabPilotoAutomatico

class TabHerramientas(QWidget):
    """
    Contenedor principal para los módulos de administración, extracción
    y configuración del sistema. Utiliza un sistema de subpestañas.
    """
    
    datos_actualizados_global = Signal()

    def __init__(self): 
        super().__init__()
        
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(20, 20, 20, 20)

        etiqueta_titulo = QLabel("Panel de Herramientas del Sistema")
        etiqueta_titulo.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        self.layout_principal.addWidget(etiqueta_titulo)

        self.pestañas_internas = QTabWidget()
        self.layout_principal.addWidget(self.pestañas_internas)

        # Instanciación de las subpestañas operativas
        self.vista_extraer = SubTabExtraer()
        self.vista_extraer.extraccion_completada.connect(self.datos_actualizados_global.emit)
        self.vista_exportar = SubTabExportar()
        self.vista_puntajes = SubTabPuntajes()
        self.vista_piloto = SubTabPilotoAutomatico()

        # Nombres de pestañas formalizados (Sin caracteres gráficos)
        self.pestañas_internas.addTab(self.vista_extraer, "Extracción de Datos")
        self.pestañas_internas.addTab(self.vista_exportar, "Exportación y Reportes")
        self.pestañas_internas.addTab(self.vista_puntajes, "Configuración de Reglas y Puntajes")
        self.pestañas_internas.addTab(self.vista_piloto, "Piloto Automático")
        
        self.aplicar_estilo_pestañas()

    def aplicar_estilo_pestañas(self):
        """Aplica las reglas CSS específicas para la navegación de subpestañas."""
        self.pestañas_internas.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background: white;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #f0f0f0;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #0078d4;
                font-weight: bold;
            }
        """)