from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, 
                               QPushButton, QDialog, QLabel, QLineEdit, QSpinBox, 
                               QDialogButtonBox, QMenu, QMessageBox, QComboBox, QGroupBox, QFormLayout)
from PySide6.QtCore import Qt

from src.UI.controllers.puntajes_controller import ControladorPuntajes
from src.bd.database import SessionLocal
from src.bd.models import PalabraClave

class DialogoPalabra(QDialog):
    """Formulario emergente para la creación o edición de reglas de negocio."""
    
    def __init__(self, parent=None, data=None, categorias_disponibles=[]):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Regla de Negocio")
        self.setFixedWidth(400)
        
        self.layout_principal = QVBoxLayout(self)
        
        self.layout_principal.addWidget(QLabel("Palabra o Frase Clave:"))
        self.input_palabra = QLineEdit()
        self.layout_principal.addWidget(self.input_palabra)
        
        self.layout_principal.addWidget(QLabel("Categoría de Agrupación:"))
        self.input_categoria = QComboBox()
        self.input_categoria.setEditable(True)
        if categorias_disponibles:
            self.input_categoria.addItems(categorias_disponibles)
        self.input_categoria.setPlaceholderText("Seleccione o ingrese nueva...")
        self.layout_principal.addWidget(self.input_categoria)

        self.layout_principal.addSpacing(15)
        
        grupo_puntajes = QGroupBox("Asignación de Pesos (Puntajes)")
        layout_puntajes = QFormLayout(grupo_puntajes)
        
        self.spin_titulo = QSpinBox()
        self.spin_titulo.setRange(-1000, 1000)
        layout_puntajes.addRow("Peso en Título:", self.spin_titulo)
        
        self.spin_desc = QSpinBox()
        self.spin_desc.setRange(-1000, 1000)
        layout_puntajes.addRow("Peso en Descripción:", self.spin_desc)
        
        self.spin_prod = QSpinBox()
        self.spin_prod.setRange(-1000, 1000)
        layout_puntajes.addRow("Peso en Productos:", self.spin_prod)
        
        self.layout_principal.addWidget(grupo_puntajes)
        
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        self.layout_principal.addWidget(botones)
        
        if data:
            self.input_palabra.setText(data.palabra)
            self.input_categoria.setCurrentText(data.categoria)
            self.spin_titulo.setValue(data.puntaje_titulo)
            self.spin_desc.setValue(data.puntaje_descripcion)
            self.spin_prod.setValue(data.puntaje_productos)
        else:
            self.spin_titulo.setValue(10)

    def obtener_datos(self):
        return {
            "palabra": self.input_palabra.text().strip(),
            "categoria": self.input_categoria.currentText().strip(),
            "puntaje_titulo": self.spin_titulo.value(),
            "puntaje_descripcion": self.spin_desc.value(),
            "puntaje_productos": self.spin_prod.value()
        }


class SubTabPalabras(QWidget):
    """Vista principal para la gestión del diccionario de evaluación."""
    
    def __init__(self):
        super().__init__()
        self.controlador = ControladorPuntajes()
        
        self.layout_principal = QVBoxLayout(self)
        
        barra_superior = QHBoxLayout()
        boton_nueva = QPushButton("Agregar Nueva Regla")
        boton_nueva.clicked.connect(lambda: self.abrir_editor(None))
        boton_nueva.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold; padding: 5px;")
        
        boton_refrescar = QPushButton("Actualizar Vista")
        boton_refrescar.clicked.connect(self.cargar_datos)
        
        barra_superior.addWidget(boton_nueva)
        barra_superior.addStretch()
        barra_superior.addWidget(boton_refrescar)
        self.layout_principal.addLayout(barra_superior)
        
        self.arbol = QTreeWidget()
        self.arbol.setHeaderLabels(["Regla / Categoría", "Distribución de Puntaje"]) 
        self.arbol.setColumnWidth(0, 400) 
        self.arbol.setContextMenuPolicy(Qt.CustomContextMenu)
        self.arbol.customContextMenuRequested.connect(self.mostrar_menu_contextual)
        
        self.layout_principal.addWidget(self.arbol)
        self.cargar_datos()

    def cargar_datos(self):
        self.arbol.clear()
        palabras = self.controlador.obtener_todas_palabras()
        
        grupos = {}
        for p in palabras:
            cat = p.categoria if p.categoria else "Sin Categoría"
            if cat not in grupos: grupos[cat] = []
            grupos[cat].append(p)
            
        for categoria, lista_items in grupos.items():
            rama = QTreeWidgetItem(self.arbol)
            rama.setText(0, categoria)
            rama.setExpanded(True)
            rama.setBackground(0, Qt.lightGray)
            
            for item_db in lista_items:
                hoja = QTreeWidgetItem(rama)
                hoja.setText(0, item_db.palabra)
                
                resumen = f"Tit: {item_db.puntaje_titulo} | Desc: {item_db.puntaje_descripcion} | Prod: {item_db.puntaje_productos}"
                hoja.setText(1, resumen)
                hoja.setData(0, Qt.UserRole, item_db.id)

    def mostrar_menu_contextual(self, posicion):
        item = self.arbol.itemAt(posicion)
        if not item or item.parent() is None: return
            
        menu = QMenu()
        accion_editar = menu.addAction("[Acción] Modificar Regla")
        accion_borrar = menu.addAction("[Acción] Eliminar Regla")
        
        accion_seleccionada = menu.exec(self.arbol.viewport().mapToGlobal(posicion))
        
        if accion_seleccionada == accion_editar:
            id_db = item.data(0, Qt.UserRole)
            # Solicitamos el objeto al controlador 
            obj = self.controlador.obtener_palabra_por_id(id_db)
            if obj:
                self.abrir_editor(obj)
            else:
                QMessageBox.warning(self, "Error", "No se pudo recuperar la información de la regla.")
            
        elif accion_seleccionada == accion_borrar:
            id_db = item.data(0, Qt.UserRole)
            if QMessageBox.question(self, "Confirmación Requerida", "¿Está seguro de eliminar esta regla del sistema?") == QMessageBox.Yes:
                self.controlador.borrar_palabra(id_db)
                self.cargar_datos()

    def abrir_editor(self, data_db):
        todas = self.controlador.obtener_todas_palabras()
        categorias_raw = [p.categoria for p in todas if p.categoria]
        categorias_unicas = sorted(list(set(categorias_raw)))
        
        dialogo = DialogoPalabra(self, data=data_db, categorias_disponibles=categorias_unicas)
        
        if dialogo.exec():
            datos = dialogo.obtener_datos()
            id_palabra = data_db.id if data_db else None
            
            exito = self.controlador.guardar_palabra(
                id_palabra, 
                datos["palabra"], 
                datos["categoria"], 
                datos["puntaje_titulo"],      
                datos["puntaje_descripcion"], 
                datos["puntaje_productos"]
            )
            
            if exito:
                self.cargar_datos()
            else:
                QMessageBox.critical(self, "Error de Persistencia", "No fue posible registrar los cambios en la base de datos.")