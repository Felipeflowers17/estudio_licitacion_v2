from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from src.UI.widgets.subTabs_Herramientas.tab_palabras import SubTabPalabras
from src.UI.widgets.subTabs_Herramientas.tab_organismos import SubTabOrganismos

class SubTabPuntajes(QWidget):
    """
    Contenedor de segundo nivel para organizar las vistas de configuración
    de las reglas de negocio (Palabras clave y valoración de Organismos).
    """
    def __init__(self):
        super().__init__()
        self.layout_principal = QVBoxLayout(self)
        
        self.pestañas_internas = QTabWidget()
        
        self.vista_palabras = SubTabPalabras()
        self.vista_organismos = SubTabOrganismos() 
        
        # Eliminación de caracteres gráficos en las etiquetas
        self.pestañas_internas.addTab(self.vista_palabras, "Reglas y Palabras Clave")
        self.pestañas_internas.addTab(self.vista_organismos, "Directorio de Organismos")
        
        self.layout_principal.addWidget(self.pestañas_internas)