from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTimeEdit, QPushButton, QGroupBox)
from PySide6.QtCore import Qt, QTime, QTimer
from datetime import datetime, timedelta

from src.UI.workers.scraping_worker import TrabajadorExtraccion

class SubTabPilotoAutomatico(QWidget):
    """
    Gestiona la programación asíncrona de extracciones periódicas
    sin intervención manual del usuario.
    """
    def __init__(self):
        super().__init__()
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setAlignment(Qt.AlignTop)

        etiqueta_titulo = QLabel("Gestor de Ejecución Automatizada")
        etiqueta_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        self.layout_principal.addWidget(etiqueta_titulo)

        grupo_configuracion = QGroupBox("Programación Diaria")
        layout_configuracion = QVBoxLayout(grupo_configuracion)

        instruccion = QLabel("Configure la hora de ejecución del proceso automatizado.\n"
                             "Requisito: La aplicación debe permanecer en ejecución.")
        instruccion.setStyleSheet("color: #666; font-style: italic;")
        layout_configuracion.addWidget(instruccion)

        fila_hora = QHBoxLayout()
        fila_hora.addWidget(QLabel("Hora de lanzamiento (HH:MM):"))
        
        self.selector_hora = QTimeEdit()
        self.selector_hora.setDisplayFormat("HH:mm")
        self.selector_hora.setTime(QTime(20, 30)) 
        self.selector_hora.setFixedWidth(100)
        
        fila_hora.addWidget(self.selector_hora)
        fila_hora.addStretch()
        layout_configuracion.addLayout(fila_hora)

        self.layout_principal.addWidget(grupo_configuracion)

        self.boton_activar = QPushButton("Inicializar Servicio Automático")
        self.boton_activar.setFixedHeight(45)
        self.boton_activar.setCursor(Qt.PointingHandCursor)
        self.boton_activar.setStyleSheet(self.obtener_estilo_boton(False))
        self.boton_activar.clicked.connect(self.alternar_estado_servicio)
        
        self.layout_principal.addSpacing(20)
        self.layout_principal.addWidget(self.boton_activar)

        self.etiqueta_estado = QLabel("[ESTADO: INACTIVO]")
        self.etiqueta_estado.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px; color: #555;")
        self.layout_principal.addWidget(self.etiqueta_estado)

        self.etiqueta_registro = QLabel("") 
        self.etiqueta_registro.setStyleSheet("color: #0078d4;")
        self.layout_principal.addWidget(self.etiqueta_registro)

        # Reloj interno de comprobación
        self.temporizador = QTimer(self)
        self.temporizador.timeout.connect(self.evaluar_condicion_ejecucion)
        self.servicio_activo = False
        
        self.fecha_ultima_operacion = None 
        self.trabajador = None

    def obtener_estilo_boton(self, activo: bool) -> str:
        """Retorna la directiva CSS correspondiente al estado del servicio."""
        if activo:
            return """
                QPushButton { background-color: #d32f2f; color: white; font-weight: bold; border-radius: 5px; }
                QPushButton:hover { background-color: #b71c1c; }
            """
        else:
            return """
                QPushButton { background-color: #388e3c; color: white; font-weight: bold; border-radius: 5px; }
                QPushButton:hover { background-color: #2e7d32; }
            """

    def alternar_estado_servicio(self):
        """Gestiona el encendido y apagado del daemon de recolección."""
        if self.servicio_activo:
            self.temporizador.stop()
            self.servicio_activo = False
            self.selector_hora.setEnabled(True) 
            self.boton_activar.setText("Inicializar Servicio Automático")
            self.boton_activar.setStyleSheet(self.obtener_estilo_boton(False))
            self.etiqueta_estado.setText("[ESTADO: INACTIVO]")
            self.etiqueta_registro.setText("")
        else:
            self.temporizador.start(60000) 
            self.servicio_activo = True
            self.selector_hora.setEnabled(False) 
            self.boton_activar.setText("Detener Servicio Automático")
            self.boton_activar.setStyleSheet(self.obtener_estilo_boton(True))
            
            hora_obj = self.selector_hora.time().toString("HH:mm")
            self.etiqueta_estado.setText(f"[ESTADO: ACTIVO] - En espera hasta las {hora_obj}")

    def evaluar_condicion_ejecucion(self):
        """Validador ejecutado por el temporizador cada minuto."""
        if not self.servicio_activo: return

        ahora = datetime.now()
        hora_actual = ahora.time()
        hora_configurada = self.selector_hora.time()

        if (hora_actual.hour == hora_configurada.hour() and 
            hora_actual.minute == hora_configurada.minute()):
            
            if self.fecha_ultima_operacion != ahora.date():
                self.lanzar_extraccion_programada(ahora)

    def lanzar_extraccion_programada(self, fecha_base: datetime):
        """Orquesta el inicio del Worker para analizar el día anterior."""
        self.fecha_ultima_operacion = fecha_base.date() 
        
        dia_objetivo = fecha_base - timedelta(days=1)
        
        self.etiqueta_estado.setText(f"[ESTADO: PROCESANDO] - Analizando registros del {dia_objetivo.strftime('%d/%m/%Y')}")
        
        self.trabajador = TrabajadorExtraccion(dia_objetivo, dia_objetivo) 
        self.trabajador.progreso.connect(self.actualizar_registro_visual)
        self.trabajador.error.connect(self.registrar_fallo)
        self.trabajador.finalizado.connect(self.notificar_culminacion)
        self.trabajador.start()

    def actualizar_registro_visual(self, mensaje: str):
        texto_limpio = mensaje.strip().split('\n')[-1]
        self.etiqueta_registro.setText(texto_limpio)

    def notificar_culminacion(self):
        hora_obj = self.selector_hora.time().toString("HH:mm")
        self.etiqueta_estado.setText(f"[ESTADO: ACTIVO] - Operación exitosa. Próxima ejecución: {hora_obj}")
        self.etiqueta_registro.setText("Ciclo completado correctamente.")

    def registrar_fallo(self, descripcion_error: str):
        self.etiqueta_estado.setText("[ESTADO: ERROR] - Interrupción en el ciclo automatizado")
        self.etiqueta_registro.setText(f"Detalle técnico: {descripcion_error}")