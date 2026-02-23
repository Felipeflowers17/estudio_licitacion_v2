from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, 
                               QVBoxLayout, QListWidget, QListWidgetItem, 
                               QStackedWidget, QLabel)
from PySide6.QtGui import QFont
from PySide6.QtCore import QSize

from src.UI.widgets.tab_candidatas import TabCandidatas
from src.UI.widgets.tab_seguimiento import TabSeguimiento
from src.UI.widgets.tab_ofertadas import TabOfertadas
from src.UI.widgets.tab_herramientas import TabHerramientas

class VentanaPrincipal(QMainWindow):
    """
    Ventana principal de la aplicación.
    Gestiona la navegación lateral y el contenedor de las distintas vistas (pestañas).
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor de Licitaciones - Sistema de Evaluación Automática")
        self.resize(1100, 750)

        self.widget_principal = QWidget()
        self.setCentralWidget(self.widget_principal)
        
        self.layout_principal = QHBoxLayout(self.widget_principal)
        self.layout_principal.setContentsMargins(0, 0, 0, 0)
        self.layout_principal.setSpacing(0)

        self.crear_menu_lateral()
        self.crear_area_contenido()

        self.lista_menu.currentRowChanged.connect(self.cambiar_pagina)
        self.aplicar_estilo_moderno()
        
        # Seleccionar la primera opción por defecto
        self.lista_menu.setCurrentRow(0)

    def crear_menu_lateral(self):
        """Construye el panel de navegación izquierdo."""
        self.contenedor_menu = QWidget()
        self.contenedor_menu.setFixedWidth(250)
        self.contenedor_menu.setObjectName("MenuContainer")
        
        layout_menu = QVBoxLayout(self.contenedor_menu)
        
        titulo = QLabel("Navegación Principal")
        titulo.setFont(QFont("Segoe UI", 12, QFont.Bold))
        titulo.setStyleSheet("color: #555; padding: 10px;")
        layout_menu.addWidget(titulo)

        self.lista_menu = QListWidget()
        self.lista_menu.setObjectName("MenuLista")
        
        self.agregar_boton_menu("Licitaciones Candidatas")
        self.agregar_boton_menu("Licitaciones en Seguimiento")
        self.agregar_boton_menu("Licitaciones Ofertadas")
        self.agregar_boton_menu("Herramientas del Sistema")

        layout_menu.addWidget(self.lista_menu)
        self.layout_principal.addWidget(self.contenedor_menu)

    def agregar_boton_menu(self, texto: str):
        """Añade un elemento a la lista de navegación."""
        item = QListWidgetItem(texto)
        item.setSizeHint(QSize(0, 45))
        self.lista_menu.addItem(item)

    def crear_area_contenido(self):
        """Instancia e inicializa el contenedor dinámico de vistas."""
        self.pila_vistas = QStackedWidget()
        self.pila_vistas.setObjectName("ContenidoStack")
        
        self.vista_candidatas = TabCandidatas()
        self.vista_seguimiento = TabSeguimiento()
        self.vista_ofertadas = TabOfertadas()
        self.vista_herramientas = TabHerramientas()

        self.pila_vistas.addWidget(self.vista_candidatas)
        self.pila_vistas.addWidget(self.vista_seguimiento)
        self.pila_vistas.addWidget(self.vista_ofertadas)
        self.pila_vistas.addWidget(self.vista_herramientas)
        
        # Conexión del bus de eventos: Escuchamos las señales de movimiento de datos
        self.vista_candidatas.datos_actualizados_global.connect(self.invalidar_caches)
        self.vista_seguimiento.datos_actualizados_global.connect(self.invalidar_caches)
        self.vista_ofertadas.datos_actualizados_global.connect(self.invalidar_caches)
        
        self.layout_principal.addWidget(self.pila_vistas)

    def invalidar_caches(self):
        """Ensucia las banderas de las tablas. Forzará una recarga cuando el usuario las visite."""
        self.vista_candidatas.marcar_como_desactualizada()
        self.vista_seguimiento.marcar_como_desactualizada()
        self.vista_ofertadas.marcar_como_desactualizada()

    def cambiar_pagina(self, indice: int):
        """Alterna entre las diferentes vistas y delega la actualización condicional."""
        self.pila_vistas.setCurrentIndex(indice)
        widget_actual = self.pila_vistas.currentWidget()
        if hasattr(widget_actual, 'actualizar_datos'):
            widget_actual.actualizar_datos()

    def aplicar_estilo_moderno(self):
        """Aplica las reglas CSS generales para la interfaz."""
        estilo = """
            QMainWindow { background-color: #f3f3f3; }
            QWidget#MenuContainer { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
            QListWidget { border: none; background-color: transparent; outline: none; }
            QListWidget::item { border-radius: 8px; padding: 5px; margin: 5px 10px; color: #333; font-family: "Segoe UI"; font-size: 14px; }
            QListWidget::item:hover { background-color: #f0f0f0; }
            QListWidget::item:selected { background-color: #e5f3ff; color: #0078d4; font-weight: bold; }
            QTableWidget { background-color: white; border: 1px solid #e0e0e0; border-radius: 8px; gridline-color: #f0f0f0; }
            QHeaderView::section { background-color: white; border: none; border-bottom: 2px solid #0078d4; padding: 8px; font-weight: bold; color: #444; }
        """
        self.setStyleSheet(estilo)