from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt
from src.config.constantes import TAMANIO_PAGINA_TABLAS, EtapaLicitacion
from src.UI.widgets.tab_listado_base import TabListadoBase

class TabSeguimiento(TabListadoBase):  
    """Vista operativa para las licitaciones marcadas para evaluación profunda o seguimiento."""
    def __init__(self):
        super().__init__()

    def cargar_datos(self):
        desplazamiento = self.pagina_actual * TAMANIO_PAGINA_TABLAS
        licitaciones = self.repositorio.obtener_seguimiento(offset=desplazamiento)
        self.poblar_tabla(licitaciones, Qt.blue)

    def mostrar_menu_contextual(self, posicion):
        item = self.tabla.itemAt(posicion)
        if not item: return
        
        menu = QMenu()
        accion_candidata = menu.addAction("[Mover] A Candidatas")
        accion_ofertada = menu.addAction("[Mover] A Ofertadas")
        
        accion_seleccionada = menu.exec(self.tabla.viewport().mapToGlobal(posicion))
        
        fila = item.row()
        codigo = self.tabla.item(fila, 1).text()
        
        if accion_seleccionada == accion_candidata:
            self.mover_etapa(codigo, EtapaLicitacion.CANDIDATA.value)
        elif accion_seleccionada == accion_ofertada:
            self.mover_etapa(codigo, EtapaLicitacion.OFERTADA.value)