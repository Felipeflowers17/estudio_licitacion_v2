from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QMessageBox)
from PySide6.QtCore import Qt, Signal

from src.repositories.licitaciones_repository import RepositorioLicitaciones
from src.UI.widgets.tab_detalle_licitacion import DialogoDetalleLicitacion

class TabListadoBase(QWidget):
    """
    Clase padre que concentra la lógica estructural y visual de las tablas de licitaciones.
    Implementa el principio DRY para evitar código duplicado en las vistas derivadas.
    """
    
    # Señal de transmisión: Avisará a la ventana principal cuando un registro cambie de etapa
    datos_actualizados_global = Signal()

    def __init__(self):
        super().__init__()
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(20, 20, 20, 20) 
        self.repositorio = RepositorioLicitaciones()
        
        # Patrón Dirty Flag: Asumimos que al inicio los datos deben cargarse
        self.necesita_actualizacion = True
        
        self.tabla = QTableWidget()
        self.configurar_tabla()
        self.layout_principal.addWidget(self.tabla)

    def configurar_tabla(self):
        columnas = ["Puntaje", "Código Externo", "Nombre de Licitación", "Fecha de Cierre", "Estado"]
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        self.tabla.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabla.customContextMenuRequested.connect(self.mostrar_menu_contextual)
        self.tabla.cellDoubleClicked.connect(self.abrir_ficha_tecnica)
    
    def abrir_ficha_tecnica(self, fila: int, columna: int):
        item_codigo = self.tabla.item(fila, 1) 
        if item_codigo:
            codigo = item_codigo.text()
            
            licitacion_completa = self.repositorio.obtener_licitacion_por_codigo(codigo)
            
            if licitacion_completa:
                dialogo = DialogoDetalleLicitacion(licitacion_completa, self)
                dialogo.exec()
            else:
                QMessageBox.warning(self, "Error de Datos", f"No fue posible recuperar los detalles de la licitación {codigo}.")

    def poblar_tabla(self, licitaciones: list, color_puntaje: Qt.GlobalColor):
        """Llena la cuadrícula con los datos inyectados por la clase hija."""
        self.tabla.setRowCount(0)
        self.tabla.setRowCount(len(licitaciones))
        
        for fila, licitacion in enumerate(licitaciones):
            item_puntaje = QTableWidgetItem(str(licitacion.puntaje))
            item_puntaje.setForeground(color_puntaje)
            item_puntaje.setTextAlignment(Qt.AlignCenter)
            item_puntaje.setToolTip(licitacion.justificacion_puntaje or "Sin análisis detallado.")
            
            self.tabla.setItem(fila, 0, item_puntaje)
            self.tabla.setItem(fila, 1, QTableWidgetItem(licitacion.codigo_externo))
            self.tabla.setItem(fila, 2, QTableWidgetItem(licitacion.nombre))
            
            fecha_texto = licitacion.fecha_cierre.strftime("%d-%m-%Y %H:%M") if licitacion.fecha_cierre else "No definida"
            self.tabla.setItem(fila, 3, QTableWidgetItem(fecha_texto))
            
            estado = licitacion.estado.descripcion if licitacion.estado else str(licitacion.codigo_estado)
            self.tabla.setItem(fila, 4, QTableWidgetItem(estado))

        # Una vez poblada la tabla, marcamos que los datos ya están frescos
        self.necesita_actualizacion = False

    def mover_etapa(self, codigo: str, nueva_etapa: str):
        if self.repositorio.mover_licitacion(codigo, nueva_etapa):
            # 1. Recargamos la pestaña actual para que el registro desaparezca
            self.cargar_datos() 
            # 2. Emitimos la señal para informar al sistema que hubo un movimiento
            self.datos_actualizados_global.emit()
        else:
            QMessageBox.warning(self, "Error de Sistema", f"No fue posible actualizar el registro {codigo}.")
            
    def actualizar_datos(self):
        """Método de entrada al cambiar de pestaña. Evaluación condicional."""
        if self.necesita_actualizacion:
            self.cargar_datos()

    def marcar_como_desactualizada(self):
        """Permite que el sistema externo ensucie la bandera de esta vista."""
        self.necesita_actualizacion = True

    # Métodos abstractos que deben ser implementados por las clases hijas
    def cargar_datos(self):
        pass

    def mostrar_menu_contextual(self, posicion):
        pass