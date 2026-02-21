from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt
from src.UI.widgets.tab_listado_base import TabListadoBase

class TabOfertadas(TabListadoBase):  
    """Vista de archivo y control para las licitaciones en las que ya se presentó oferta."""
    def __init__(self):
        super().__init__()
        self.cargar_datos()

    def cargar_datos(self):
        licitaciones = self.repositorio.obtener_ofertadas()
        self.poblar_tabla(licitaciones, Qt.darkMagenta)

    def mostrar_menu_contextual(self, posicion):
        item = self.tabla.itemAt(posicion)
        if not item: return
        
        menu = QMenu()
        accion_candidata = menu.addAction("[Mover] A Candidatas")
        accion_seguimiento = menu.addAction("[Mover] A Seguimiento")
        
        accion_seleccionada = menu.exec(self.tabla.viewport().mapToGlobal(posicion))
        
        fila = item.row()
        codigo = self.tabla.item(fila, 1).text()
        
        if accion_seleccionada == accion_candidata:
            self.mover_etapa(codigo, "candidata")
        elif accion_seleccionada == accion_seguimiento:
            self.mover_etapa(codigo, "seguimiento")