from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QMessageBox)
from PySide6.QtCore import Qt, Signal

from src.repositories.licitaciones_repository import RepositorioLicitaciones
from src.UI.widgets.tab_detalle_licitacion import DialogoDetalleLicitacion
from src.config.constantes import TAMANIO_PAGINA_TABLAS

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
        
        # Estado de paginación
        self.pagina_actual = 0
        self.necesita_actualizacion = True
        
        self.tabla = QTableWidget()
        self.configurar_tabla()
        self.layout_principal.addWidget(self.tabla)

        # Controles de navegación de página
        self.crear_barra_paginacion()

    def crear_barra_paginacion(self):
        """Construye la botonera inferior para navegar entre páginas de resultados."""
        layout_paginacion = QHBoxLayout()
        layout_paginacion.addStretch()

        self.boton_anterior = QPushButton("Página Anterior")
        self.boton_anterior.setFixedWidth(120)
        self.boton_anterior.setEnabled(False)
        self.boton_anterior.clicked.connect(self.ir_pagina_anterior)

        self.etiqueta_pagina = QLabel("Página: 1")
        self.etiqueta_pagina.setStyleSheet("font-weight: bold; padding: 0 10px;")

        self.boton_siguiente = QPushButton("Página Siguiente")
        self.boton_siguiente.setFixedWidth(120)
        self.boton_siguiente.clicked.connect(self.ir_pagina_siguiente)

        layout_paginacion.addWidget(self.boton_anterior)
        layout_paginacion.addWidget(self.etiqueta_pagina)
        layout_paginacion.addWidget(self.boton_siguiente)
        
        self.layout_principal.addLayout(layout_paginacion)

    def ir_pagina_siguiente(self):
        self.pagina_actual += 1
        self.cargar_datos()
        self.actualizar_estado_paginacion()

    def ir_pagina_anterior(self):
        if self.pagina_actual > 0:
            self.pagina_actual -= 1
            self.cargar_datos()
            self.actualizar_estado_paginacion()
    
    def actualizar_estado_paginacion(self):
        """Refresca las etiquetas y el estado de los botones de navegación."""
        self.etiqueta_pagina.setText(f"Página: {self.pagina_actual + 1}")
        self.boton_anterior.setEnabled(self.pagina_actual > 0)
        
        # Si la tabla tiene menos registros que el tamaño de página, asumimos que es la última
        self.boton_siguiente.setEnabled(self.tabla.rowCount() == TAMANIO_PAGINA_TABLAS)

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
            # Al forzar una actualización desde fuera (movimiento de etapa), reiniciamos a página 0
            self.pagina_actual = 0
            self.cargar_datos()
            self.actualizar_estado_paginacion()

    def marcar_como_desactualizada(self):
        """Permite que el sistema externo ensucie la bandera de esta vista."""
        self.necesita_actualizacion = True

    # Métodos abstractos que deben ser implementados por las clases hijas
    def cargar_datos(self):
        pass

    def mostrar_menu_contextual(self, posicion):
        pass