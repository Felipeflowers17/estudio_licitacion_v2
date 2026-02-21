from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, 
                               QPushButton, QLineEdit, QMenu, QInputDialog, QMessageBox)
from PySide6.QtCore import Qt
from src.UI.controllers.organismos_controller import ControladorOrganismos

class SubTabOrganismos(QWidget):
    """Interfaz para la gestión y ponderación de las instituciones compradoras."""
    
    def __init__(self):
        super().__init__()
        self.controlador = ControladorOrganismos()
        self.items_organismos = [] 
        
        self.layout_principal = QVBoxLayout(self)
        
        barra_superior = QHBoxLayout()
        
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("Ingrese nombre del organismo para filtrar...")
        self.input_buscar.textChanged.connect(self.filtrar_lista) 
        
        boton_refrescar = QPushButton("Actualizar Directorio")
        boton_refrescar.clicked.connect(self.cargar_datos)
        
        barra_superior.addWidget(self.input_buscar)
        barra_superior.addWidget(boton_refrescar)
        self.layout_principal.addLayout(barra_superior)
        
        self.arbol = QTreeWidget()
        self.arbol.setHeaderLabels(["Nombre de Institución", "Código Interno", "Valoración Automática"])
        self.arbol.setColumnWidth(0, 450) 
        self.arbol.setColumnWidth(1, 100)
        self.arbol.setContextMenuPolicy(Qt.CustomContextMenu) 
        self.arbol.customContextMenuRequested.connect(self.mostrar_menu_contextual)
        
        self.layout_principal.addWidget(self.arbol)
        self.cargar_datos()

    def cargar_datos(self):
        self.arbol.clear()
        self.items_organismos = [] 
        
        datos = self.controlador.obtener_todos()
        
        grupos = {}
        for org in datos:
            if not org.nombre: continue
            
            letra = org.nombre[0].upper()
            if not letra.isalpha(): 
                letra = "#" 
            
            if letra not in grupos: grupos[letra] = []
            grupos[letra].append(org)
            
        for letra in sorted(grupos.keys()):
            rama_letra = QTreeWidgetItem(self.arbol)
            rama_letra.setText(0, f"--- Grupo {letra} ---")
            rama_letra.setExpanded(False) 
            rama_letra.setBackground(0, Qt.lightGray)
            
            for org in grupos[letra]:
                hoja = QTreeWidgetItem(rama_letra)
                hoja.setText(0, org.nombre)
                hoja.setText(1, org.codigo)
                hoja.setText(2, str(org.puntaje))
                
                if org.puntaje > 0:
                    hoja.setForeground(2, Qt.darkGreen) 
                elif org.puntaje < 0:
                    hoja.setForeground(2, Qt.red) 

                hoja.setData(0, Qt.UserRole, org.codigo)
                self.items_organismos.append((hoja, org.nombre.lower()))

    def filtrar_lista(self, texto: str):
        texto = texto.lower()
        if not texto:
            for i in range(self.arbol.topLevelItemCount()):
                self.arbol.topLevelItem(i).setHidden(False)
            return

        for i in range(self.arbol.topLevelItemCount()):
            rama = self.arbol.topLevelItem(i)
            rama_visible = False
            
            for j in range(rama.childCount()):
                hijo = rama.child(j)
                nombre_org = hijo.text(0).lower()
                
                if texto in nombre_org:
                    hijo.setHidden(False)
                    rama_visible = True 
                else:
                    hijo.setHidden(True)
            
            rama.setHidden(not rama_visible)
            if rama_visible:
                rama.setExpanded(True) 

    def mostrar_menu_contextual(self, posicion):
        item = self.arbol.itemAt(posicion)
        if not item or item.childCount() > 0: return

        menu = QMenu()
        accion_prioritario = menu.addAction("[Asignar] Prioritario (+)")
        accion_no_deseado = menu.addAction("[Asignar] No Deseado (-)")
        accion_neutro = menu.addAction("[Asignar] Neutro (0)")
        
        accion_seleccionada = menu.exec(self.arbol.viewport().mapToGlobal(posicion))
        
        codigo = item.data(0, Qt.UserRole)
        nuevo_puntaje = None
        
        if accion_seleccionada == accion_prioritario:
            puntos, ok = QInputDialog.getInt(self, "Valoración Positiva", "Puntaje a incrementar:", 100, 1, 1000)
            if ok: nuevo_puntaje = puntos
            
        elif accion_seleccionada == accion_no_deseado:
            puntos, ok = QInputDialog.getInt(self, "Valoración Negativa", "Puntaje a penalizar:", -100, -1000, -1)
            if ok: nuevo_puntaje = puntos
            
        elif accion_seleccionada == accion_neutro:
            nuevo_puntaje = 0
            
        if nuevo_puntaje is not None:
            if self.controlador.actualizar_puntaje(codigo, nuevo_puntaje):
                item.setText(2, str(nuevo_puntaje))
                if nuevo_puntaje > 0:
                    item.setForeground(2, Qt.darkGreen)
                elif nuevo_puntaje < 0:
                    item.setForeground(2, Qt.red)
                else:
                    item.setForeground(2, Qt.black)
            else:
                QMessageBox.warning(self, "Error de Sistema", "No fue posible registrar la actualización.")