from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, 
                               QPushButton, QGroupBox, QFileDialog, QMessageBox, QLabel, QApplication)
from PySide6.QtCore import Qt

# Importamos la clase del servicio refactorizado
from src.services.exportador import ServicioExportador

class SubTabExportar(QWidget):
    """
    Subpestaña dedicada a la configuración y generación de reportes 
    y respaldos de la base de datos hacia formatos estandarizados.
    """
    def __init__(self):
        super().__init__()
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setAlignment(Qt.AlignTop)
        
        self.servicio = ServicioExportador()

        etiqueta_titulo = QLabel("Exportación y Reportes")
        etiqueta_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        self.layout_principal.addWidget(etiqueta_titulo)

        # Bloque 1: Selección de alcance de datos
        grupo_datos = QGroupBox("1. Seleccionar Entidades a Exportar")
        layout_datos = QVBoxLayout()
        
        # Eliminación de elementos gráficos (emojis) en favor de etiquetas formales
        self.casilla_candidatas = QCheckBox("[Etapa] Licitaciones Candidatas")
        self.casilla_seguimiento = QCheckBox("[Etapa] Licitaciones en Seguimiento")
        self.casilla_ofertadas = QCheckBox("[Etapa] Licitaciones Ofertadas")
        self.casilla_completa = QCheckBox("[Respaldo] Base de Datos Completa")
        self.casilla_reglas = QCheckBox("[Configuración] Reglas de Negocio y Organismos")
        
        self.casilla_candidatas.setChecked(True)

        layout_datos.addWidget(self.casilla_candidatas)
        layout_datos.addWidget(self.casilla_seguimiento)
        layout_datos.addWidget(self.casilla_ofertadas)
        layout_datos.addWidget(self.casilla_completa)
        layout_datos.addWidget(self.casilla_reglas)
        grupo_datos.setLayout(layout_datos)
        self.layout_principal.addWidget(grupo_datos)

        # Bloque 2: Selección de formato de salida
        grupo_formato = QGroupBox("2. Definir Formato de Destino")
        layout_formato = QHBoxLayout()
        
        self.casilla_xlsx = QCheckBox("Hoja de Cálculo Excel (.xlsx)")
        self.casilla_csv = QCheckBox("Archivo de Texto Plano (.csv)")
        
        self.casilla_xlsx.setChecked(True) 

        layout_formato.addWidget(self.casilla_xlsx)
        layout_formato.addWidget(self.casilla_csv)
        grupo_formato.setLayout(layout_formato)
        self.layout_principal.addWidget(grupo_formato)

        self.layout_principal.addSpacing(20)

        # Botón de acción principal
        self.boton_exportar = QPushButton("Seleccionar Directorio y Procesar")
        self.boton_exportar.setCursor(Qt.PointingHandCursor)
        self.boton_exportar.setFixedHeight(45)
        self.boton_exportar.setStyleSheet("""
            QPushButton { background-color: #2b5797; color: white; font-size: 14px; font-weight: bold; border-radius: 5px; }
            QPushButton:hover { background-color: #1e3f6f; }
        """)
        self.boton_exportar.clicked.connect(self.iniciar_exportacion)
        self.layout_principal.addWidget(self.boton_exportar)

    def iniciar_exportacion(self):
        """Valida las selecciones del usuario y orquesta el servicio de exportación."""
        if not (self.casilla_xlsx.isChecked() or self.casilla_csv.isChecked()):
            QMessageBox.warning(self, "Validación Requerida", "Es obligatorio seleccionar al menos un formato de destino.")
            return

        if not any([self.casilla_candidatas.isChecked(), self.casilla_seguimiento.isChecked(),
                    self.casilla_ofertadas.isChecked(), self.casilla_completa.isChecked(), 
                    self.casilla_reglas.isChecked()]):
            QMessageBox.warning(self, "Validación Requerida", "Debe marcar al menos un conjunto de datos para proceder con la exportación.")
            return

        directorio_destino = QFileDialog.getExistingDirectory(self, "Definir Directorio de Destino")
        if not directorio_destino:
            return 

        parametros_exportacion = {
            'candidatas': self.casilla_candidatas.isChecked(),
            'seguimiento': self.casilla_seguimiento.isChecked(),
            'ofertadas': self.casilla_ofertadas.isChecked(),
            'full_db': self.casilla_completa.isChecked(),
            'reglas': self.casilla_reglas.isChecked(),
            'xlsx': self.casilla_xlsx.isChecked(),
            'csv': self.casilla_csv.isChecked()
        }

        self.boton_exportar.setEnabled(False)
        self.boton_exportar.setText("Generando Reportes... (Por favor, espere)")
        
        # Fuerza el refresco de la interfaz gráfica antes de invocar el proceso bloqueante
        QApplication.processEvents() 

        operacion_exitosa, mensaje_resultado = self.servicio.generar_reporte(parametros_exportacion, directorio_destino)
        
        self.boton_exportar.setEnabled(True)
        self.boton_exportar.setText("Seleccionar Directorio y Procesar")

        if operacion_exitosa:
            QMessageBox.information(self, "Exportación Exitosa", mensaje_resultado)
        else:
            QMessageBox.critical(self, "Falla en Exportación", mensaje_resultado)