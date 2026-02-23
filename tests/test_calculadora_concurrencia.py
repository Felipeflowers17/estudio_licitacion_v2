import unittest
import threading
import time
from unittest.mock import MagicMock, patch

from src.services.calculadora import CalculadoraPuntajes
from src.bd.models import PalabraClave

class TestConcurrenciaCalculadora(unittest.TestCase):
    """
    Prueba de estrés para validar la seguridad entre hilos (Thread Safety) 
    de la CalculadoraPuntajes. Simula lecturas y escrituras simultáneas.
    """

    def setUp(self):
        self.reglas_mock = [
            PalabraClave(palabra="Computador", puntaje_titulo=10, puntaje_descripcion=5, puntaje_productos=1),
            PalabraClave(palabra="Servidor", puntaje_titulo=20, puntaje_descripcion=10, puntaje_productos=2)
        ]

    @patch('src.services.calculadora.SessionLocal')
    def test_condicion_de_carrera_evitada(self, mock_session_local):
        # Configuramos el mock de la base de datos para que retorne nuestras reglas falsas
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.all.return_value = self.reglas_mock
        mock_session_local.return_value = mock_db

        # Instanciamos la calculadora (que ahora tiene el Lock)
        calculadora = CalculadoraPuntajes()
        
        # Lista para almacenar excepciones capturadas dentro de los hilos
        excepciones_capturadas = []
        
        # Bandera de control para detener los hilos
        ejecutando = True

        def hilo_lector():
            """Simula el scraping masivo evaluando títulos sin parar."""
            try:
                while ejecutando:
                    calculadora.evaluar_titulo("Licitación para compra de Servidor y Computador")
                    time.sleep(0.001) # Pequeña pausa para forzar el cambio de contexto del CPU
            except Exception as e:
                excepciones_capturadas.append(f"Error Lector: {type(e).__name__} - {str(e)}")

        def hilo_escritor():
            """Simula al usuario recargando las reglas repetidamente."""
            try:
                while ejecutando:
                    calculadora.cargar_reglas_negocio()
                    time.sleep(0.002)
            except Exception as e:
                excepciones_capturadas.append(f"Error Escritor: {type(e).__name__} - {str(e)}")

        # Creamos y disparamos ambos hilos simultáneamente
        t1 = threading.Thread(target=hilo_lector)
        t2 = threading.Thread(target=hilo_escritor)

        t1.start()
        t2.start()

        # Dejamos que los hilos compitan durante 1 segundo
        time.sleep(1)
        
        # Detenemos los hilos
        ejecutando = False
        t1.join()
        t2.join()

        # Verificación: Si el Lock funciona, la lista de excepciones debe estar vacía
        if excepciones_capturadas:
            for exc in excepciones_capturadas:
                print(exc)
            self.fail("Se detectó una condición de carrera (Race Condition) u otro error de concurrencia.")
        
        print("\nTest de Concurrencia (Stress Test): PASADO. La calculadora es segura para hilos (Thread-Safe).")

if __name__ == '__main__':
    unittest.main()