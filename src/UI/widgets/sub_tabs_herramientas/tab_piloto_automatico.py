from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTimeEdit, QPushButton, QGroupBox)
from PySide6.QtCore import Qt, QTime, QTimer, QDateTime
from datetime import datetime, timedelta

from src.UI.workers.scraping_worker import TrabajadorExtraccion
from src.config.constantes import PILOTO_MAX_REINTENTOS, PILOTO_MINUTOS_REINTENTOS_BASE

class SubTabPilotoAutomatico(QWidget):
    """
    Gestiona la programación asíncrona de extracciones periódicas.
    Implementa una política de reintentos exponenciales para garantizar
    la resiliencia ante fallos de red o de la API.
    """
    def __init__(self):
        super().__init__()
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setAlignment(Qt.AlignTop)

        # Estado operativo
        self.servicio_activo = False
        self.fecha_ultima_operacion_exitosa = None 
        self.intentos_actuales = 0
        self.trabajador = None
        
        # UI Components
        self._configurar_interfaz()

        # Temporizador principal (revisión de hora cada minuto)
        self.temporizador = QTimer(self)
        self.temporizador.timeout.connect(self.evaluar_condicion_ejecucion)

    def _configurar_interfaz(self):
        """Inicializa los elementos visuales del panel."""
        etiqueta_titulo = QLabel("Gestor de Ejecución Automatizada")
        etiqueta_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        self.layout_principal.addWidget(etiqueta_titulo)

        grupo_configuracion = QGroupBox("Programación Diaria")
        layout_configuracion = QVBoxLayout(grupo_configuracion)

        instruccion = QLabel("Configure la hora de ejecución del proceso automatizado.\n"
                             "El sistema reintentará automáticamente en caso de fallos de red.")
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
        self.boton_activar.clicked.connect(self.alternar_estado_servicio)
        self.layout_principal.addWidget(self.boton_activar)

        self.etiqueta_estado = QLabel("[ESTADO: INACTIVO]")
        self.etiqueta_estado.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px; color: #555;")
        self.layout_principal.addWidget(self.etiqueta_estado)

        self.etiqueta_registro = QLabel("") 
        self.etiqueta_registro.setStyleSheet("color: #0078d4;")
        self.layout_principal.addWidget(self.etiqueta_registro)
        
        self._actualizar_estilo_boton()

    def alternar_estado_servicio(self):
        """Enciende o apaga el monitoreo de tiempo."""
        self.servicio_activo = not self.servicio_activo
        
        if self.servicio_activo:
            self.temporizador.start(60000) 
            self.selector_hora.setEnabled(False)
            hora_obj = self.selector_hora.time().toString("HH:mm")
            self.etiqueta_estado.setText(f"[ESTADO: ACTIVO] - Esperando {hora_obj}")
        else:
            self.temporizador.stop()
            self.selector_hora.setEnabled(True)
            self.etiqueta_estado.setText("[ESTADO: INACTIVO]")
            self.etiqueta_registro.setText("")

        self._actualizar_estilo_boton()

    def evaluar_condicion_ejecucion(self):
        """Comprueba si es momento de iniciar o reintentar la tarea."""
        if not self.servicio_activo: return

        ahora = datetime.now()
        hora_configurada = self.selector_hora.time()

        # Condición: Es la hora exacta Y no se ha completado hoy
        if (ahora.hour == hora_configurada.hour() and 
            ahora.minute == hora_configurada.minute()):
            
            if self.fecha_ultima_operacion_exitosa != ahora.date():
                self.intentos_actuales = 0 # Reset de intentos para el nuevo día
                self.lanzar_extraccion_programada(ahora)

    def lanzar_extraccion_programada(self, fecha_base: datetime):
        """Inicia el Worker de extracción para el día anterior."""
        dia_objetivo = fecha_base - timedelta(days=1)
        
        self.etiqueta_estado.setText(f"[ESTADO: PROCESANDO] - Analizando {dia_objetivo.strftime('%d/%m/%Y')}")
        if self.intentos_actuales > 0:
            self.etiqueta_estado.setText(self.etiqueta_estado.text() + f" (Reintento {self.intentos_actuales})")
        
        self.trabajador = TrabajadorExtraccion(dia_objetivo, dia_objetivo) 
        self.trabajador.progreso.connect(self.actualizar_registro_visual)
        self.trabajador.error.connect(self.registrar_fallo)
        self.trabajador.finalizado.connect(self.notificar_culminacion)
        self.trabajador.start()

    def registrar_fallo(self, descripcion_error: str):
        """Maneja el error y programa el reintento si corresponde."""
        if self.intentos_actuales < PILOTO_MAX_REINTENTOS:
            self.intentos_actuales += 1
            
            # Cálculo de retroceso exponencial: 5min, 10min, 20min...
            minutos_espera = PILOTO_MINUTOS_REINTENTOS_BASE * (2 ** (self.intentos_actuales - 1))
            proximo_intento = datetime.now() + timedelta(minutes=minutos_espera)
            
            self.etiqueta_estado.setText(f"[ESTADO: ERROR] - Fallo técnico. Reintento en {minutos_espera} min.")
            self.etiqueta_registro.setText(f"Próximo intento: {proximo_intento.strftime('%H:%M')}")
            
            # Programamos el reintento
            QTimer.singleShot(minutos_espera * 60000, lambda: self.lanzar_extraccion_programada(datetime.now()))
        else:
            self.etiqueta_estado.setText("[ESTADO: FALLIDO] - Se agotaron los reintentos.")
            self.etiqueta_registro.setText(f"Último error: {descripcion_error[:50]}...")

    def notificar_culminacion(self):
        """Marca el éxito y resetea el ciclo diario."""
        self.fecha_ultima_operacion_exitosa = datetime.now().date()
        self.intentos_actuales = 0
        hora_obj = self.selector_hora.time().toString("HH:mm")
        self.etiqueta_estado.setText(f"[ESTADO: ACTIVO] - Tarea completada. Siguiente: {hora_obj}")
        self.etiqueta_registro.setText("Día procesado correctamente.")

    def actualizar_registro_visual(self, mensaje: str):
        texto_limpio = mensaje.strip().split('\n')[-1]
        self.etiqueta_registro.setText(texto_limpio)

    def _actualizar_estilo_boton(self):
        if self.servicio_activo:
            self.boton_activar.setText("Detener Servicio Automático")
            self.boton_activar.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; border-radius: 5px;")
        else:
            self.boton_activar.setText("Inicializar Servicio Automático")
            self.boton_activar.setStyleSheet("background-color: #388e3c; color: white; font-weight: bold; border-radius: 5px;")