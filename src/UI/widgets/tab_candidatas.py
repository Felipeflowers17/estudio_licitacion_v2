from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt
from src.config.constantes import EtapaLicitacion
from src.UI.widgets.tab_listado_base import TabListadoBase

class TabCandidatas(TabListadoBase):  
    """Vista principal para las licitaciones recién evaluadas y filtradas."""
    def __init__(self):
        super().__init__()
        self.cargar_datos()

    def cargar_datos(self):
        licitaciones = self.repositorio.obtener_candidatas()
        self.poblar_tabla(licitaciones, Qt.darkGreen)

    def mostrar_menu_contextual(self, posicion):
        item = self.tabla.itemAt(posicion)
        if not item: return
        
        menu = QMenu()
        accion_seguimiento = menu.addAction("[Mover] A Seguimiento")
        accion_ofertada = menu.addAction("[Mover] A Ofertadas")
        
        accion_seleccionada = menu.exec(self.tabla.viewport().mapToGlobal(posicion))
        
        fila = item.row()
        codigo = self.tabla.item(fila, 1).text()
        
        if accion_seleccionada == accion_seguimiento:
            self.mover_etapa(codigo, EtapaLicitacion.SEGUIMIENTO.value)
        elif accion_seleccionada == accion_ofertada:
            self.mover_etapa(codigo, EtapaLicitacion.OFERTADA.value)