from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QDateEdit, QSpinBox, QPushButton, QGroupBox, 
                               QMessageBox, QDialog, QLineEdit, QComboBox, 
                               QDialogButtonBox, QApplication)
from PySide6.QtCore import QDate, Qt
from datetime import datetime

# Importaciones de workers y lógica de negocio
from src.scraper.recolector import RecolectorMercadoPublico
from src.services.almacenar import AlmacenadorLicitaciones
from src.services.calculadora import CalculadoraPuntajes
from src.UI.workers.scraping_worker import TrabajadorExtraccion, TrabajadorExtraccionManual

class DialogoIngresoManual(QDialog):
    """
    Formulario emergente que permite al usuario ingresar una licitación 
    específica mediante su código y destinarla a una etapa del flujo.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ingreso Manual de Licitación")
        self.setFixedWidth(450)

        self.layout_principal = QVBoxLayout(self)

        # Campo para el Código
        self.layout_principal.addWidget(QLabel("Código Externo de la Licitación:"))
        self.input_codigo = QLineEdit()
        self.input_codigo.setPlaceholderText("Ejemplo: 1234-56-LE24")
        self.layout_principal.addWidget(self.input_codigo)

        self.layout_principal.addSpacing(10)

        # Campo para la Etapa de Destino
        self.layout_principal.addWidget(QLabel("Etapa de Destino Inicial:"))
        self.combo_etapa = QComboBox()
        self.combo_etapa.addItems([
            "Licitaciones Candidatas (Flujo Normal)", 
            "En Seguimiento (Prioritaria)", 
            "Ofertadas (Postulación Activa)"
        ])
        self.layout_principal.addWidget(self.combo_etapa)

        self.layout_principal.addSpacing(15)

        # Botones de Acción
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        self.layout_principal.addWidget(botones)

    def obtener_parametros(self) -> dict:
        """Mapea la selección visual a los códigos internos de la base de datos."""
        mapa_etapas = {
            0: "candidata",
            1: "seguimiento",
            2: "ofertada"
        }
        return {
            "codigo": self.input_codigo.text().strip(),
            "etapa": mapa_etapas[self.combo_etapa.currentIndex()]
        }


class SubTabExtraer(QWidget):
    """
    Subpestaña encargada de gestionar tanto la extracción masiva asíncrona
    como la inyección manual de licitaciones específicas.
    """
    def __init__(self):
        super().__init__()
        
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setAlignment(Qt.AlignTop)

        etiqueta_titulo = QLabel("Módulos de Extracción de Datos")
        etiqueta_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px;")
        self.layout_principal.addWidget(etiqueta_titulo)

        # --- BLOQUE 1: EXTRACCIÓN MASIVA (ASÍNCRONA) ---
        grupo_masivo = QGroupBox("Extracción Masiva por Rango de Fechas")
        layout_masivo = QVBoxLayout(grupo_masivo)
        
        layout_fechas = QHBoxLayout()
        self.fecha_desde = self.crear_selector_fecha()
        layout_fechas.addWidget(QLabel("Fecha de Inicio:"))
        layout_fechas.addWidget(self.fecha_desde)
        layout_fechas.addSpacing(150)
        self.fecha_hasta = self.crear_selector_fecha()
        layout_fechas.addWidget(QLabel("Fecha de Término:"))
        layout_fechas.addWidget(self.fecha_hasta)
        layout_masivo.addLayout(layout_fechas)

        layout_paginas = QHBoxLayout()
        layout_paginas.addWidget(QLabel("Límite Máximo de Páginas a Consultar:"))
        self.selector_paginas = QSpinBox()
        self.selector_paginas.setRange(0, 1000)
        self.selector_paginas.setFixedWidth(80)
        layout_paginas.addWidget(self.selector_paginas)
        layout_paginas.addStretch()
        layout_masivo.addLayout(layout_paginas)

        self.boton_extraer = QPushButton("Iniciar Extracción Asíncrona")
        self.boton_extraer.setCursor(Qt.PointingHandCursor)
        self.boton_extraer.setFixedHeight(40)
        self.boton_extraer.setStyleSheet("""
            QPushButton { background-color: #009688; color: white; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #00796b; }
        """)
        self.boton_extraer.clicked.connect(self.iniciar_extraccion_masiva)
        layout_masivo.addWidget(self.boton_extraer)
        
        self.layout_principal.addWidget(grupo_masivo)
        self.trabajador = None

        self.layout_principal.addSpacing(15)

        # --- BLOQUE 2: EXTRACCIÓN MANUAL (SÍNCRONA) ---
        grupo_manual = QGroupBox("Extracción Específica por Código")
        layout_manual = QVBoxLayout(grupo_manual)

        instruccion_manual = QLabel("Utilice esta herramienta para forzar el ingreso y evaluación de una "
                                    "licitación específica que no haya sido capturada en el flujo diario.")
        instruccion_manual.setStyleSheet("color: #555; font-style: italic; margin-bottom: 10px;")
        layout_manual.addWidget(instruccion_manual)

        self.boton_manual = QPushButton("Ingresar Licitación Manualmente")
        self.boton_manual.setCursor(Qt.PointingHandCursor)
        self.boton_manual.setFixedHeight(40)
        self.boton_manual.setStyleSheet("""
            QPushButton { background-color: #2b5797; color: white; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #1e3f6f; }
        """)
        self.boton_manual.clicked.connect(self.iniciar_extraccion_manual)
        layout_manual.addWidget(self.boton_manual)

        self.layout_principal.addWidget(grupo_manual)


    def crear_selector_fecha(self) -> QDateEdit:
        selector = QDateEdit()
        selector.setCalendarPopup(True)
        selector.setDate(QDate.currentDate())
        selector.setDisplayFormat("dd/MM/yyyy")
        selector.setFixedWidth(120)
        return selector
    
    # --- LÓGICA DE EXTRACCIÓN MASIVA ---
    def iniciar_extraccion_masiva(self):
        fecha_inicio = self.fecha_desde.date().toPython()
        fecha_termino = self.fecha_hasta.date().toPython()
        
        if fecha_inicio > fecha_termino:
            QMessageBox.warning(self, "Validación Incorrecta", "La fecha de inicio no puede ser posterior a la de término.")
            return

        self.boton_extraer.setEnabled(False)
        self.boton_extraer.setText("Operación en Curso... (Por favor, espere)")
        
        fecha_inicio_dt = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day)
        fecha_termino_dt = datetime(fecha_termino.year, fecha_termino.month, fecha_termino.day)

        self.trabajador = TrabajadorExtraccion(fecha_inicio_dt, fecha_termino_dt)
        self.trabajador.progreso.connect(self.registrar_evento)
        self.trabajador.error.connect(self.desplegar_error)
        self.trabajador.finalizado.connect(self.notificar_finalizacion)
        self.trabajador.start()

    def registrar_evento(self, mensaje: str):
        print(f"[PROGRESO EXTRACCIÓN] {mensaje}") 

    def notificar_finalizacion(self):
        QMessageBox.information(self, "Operación Finalizada", "El proceso de recolección y análisis ha concluido exitosamente.")
        self.boton_extraer.setEnabled(True)
        self.boton_extraer.setText("Iniciar Extracción Asíncrona")

    def desplegar_error(self, mensaje_error: str):
        QMessageBox.critical(self, "Error de Ejecución", mensaje_error)
        self.boton_extraer.setEnabled(True)
        self.boton_extraer.setText("Iniciar Extracción Asíncrona")


    # --- LÓGICA DE EXTRACCIÓN MANUAL ---
    def iniciar_extraccion_manual(self):
        """Orquesta la descarga, evaluación y reubicación de una licitación individual de forma asíncrona."""
        dialogo = DialogoIngresoManual(self)
        
        if dialogo.exec():
            parametros = dialogo.obtener_parametros()
            codigo = parametros["codigo"]
            etapa_destino = parametros["etapa"]

            if not codigo:
                QMessageBox.warning(self, "Validación Requerida", "Debe ingresar un código externo válido para proceder.")
                return

            self.boton_manual.setEnabled(False)
            self.boton_manual.setText("Iniciando proceso...")

            self.trabajador_manual = TrabajadorExtraccionManual(codigo, etapa_destino)
            self.trabajador_manual.progreso.connect(lambda msg: self.boton_manual.setText(f"{msg} (Espere)"))
            self.trabajador_manual.finalizado.connect(self.procesar_resultado_manual)
            self.trabajador_manual.start()

    def procesar_resultado_manual(self, exito: bool, mensaje: str):
        """Recibe la señal de término del hilo manual y restaura la interfaz."""
        self.boton_manual.setEnabled(True)
        self.boton_manual.setText("Ingresar Licitación Manualmente")
        
        if exito:
            QMessageBox.information(self, "Operación Exitosa", mensaje)
        else:
            QMessageBox.warning(self, "Falla en la Búsqueda", mensaje)