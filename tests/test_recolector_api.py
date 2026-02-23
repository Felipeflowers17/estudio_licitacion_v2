import unittest
from unittest.mock import patch, MagicMock
import requests
from src.scraper.recolector import RecolectorMercadoPublico

class TestRecolectorMercadoPublico(unittest.TestCase):
    """
    Suite de pruebas para el cliente de la API.
    Utiliza Mocks para simular el comportamiento del servidor de Mercado Público.
    """

    @patch('src.scraper.recolector.os.getenv')
    def setUp(self, mock_getenv):
        """Configura el recolector con un ticket falso para las pruebas."""
        mock_getenv.return_value = "TICKET-PROBANDO-123"
        self.recolector = RecolectorMercadoPublico()
        # Reducimos los tiempos de espera para que los tests corran rápido
        self.recolector.min_pausa_entre_peticiones = 0.0
        self.recolector.base_retraso = 0.01

    @patch('src.scraper.recolector.requests.get')
    def test_obtener_licitaciones_diarias_exitoso(self, mock_get):
        """Prueba que el listado diario se procese correctamente cuando la API responde 200."""
        # Configuramos el comportamiento del Mock
        mock_respuesta = MagicMock()
        mock_respuesta.status_code = 200
        mock_respuesta.json.return_value = {
            "Cantidad": 2,
            "Listado": [{"CodigoExterno": "123-1-L124"}, {"CodigoExterno": "456-2-L224"}]
        }
        mock_get.return_value = mock_respuesta

        resultados = self.recolector.obtener_licitaciones_diarias("20032024")

        self.assertEqual(len(resultados), 2)
        self.assertEqual(resultados[0]["CodigoExterno"], "123-1-L124")
        mock_get.assert_called_once() # Verificamos que se llamó a la API

    @patch('src.scraper.recolector.requests.get')
    def test_obtener_detalle_no_encontrado(self, mock_get):
        """Verifica el manejo del error 404 (Licitación no encontrada)."""
        mock_respuesta = MagicMock()
        mock_respuesta.status_code = 404
        mock_get.return_value = mock_respuesta

        resultado = self.recolector.obtener_detalle_licitacion("CODIGO-INEXISTENTE")

        self.assertIsNone(resultado['datos'])
        self.assertEqual(resultado['estado'], 'no_encontrado')

    @patch('src.scraper.recolector.requests.get')
    @patch('src.scraper.recolector.time.sleep') # Mockeamos el sleep para no esperar segundos reales
    def test_reintentos_ante_error_servidor(self, mock_sleep, mock_get):
        """
        Prueba crítica: Verifica que si la API falla con error 500, 
        el recolector intente descargar nuevamente según el límite configurado.
        """
        # Configuramos para que siempre devuelva error 500
        mock_respuesta = MagicMock()
        mock_respuesta.status_code = 500
        mock_get.return_value = mock_respuesta

        resultado = self.recolector.obtener_detalle_licitacion("5555-66-L124")

        # Debe haber intentado el número máximo de veces definido en el constructor
        self.assertEqual(mock_get.call_count, self.recolector.max_intentos)
        self.assertEqual(resultado['estado'], 'error_servidor')

    @patch('src.scraper.recolector.requests.get')
    def test_manejo_excepcion_red(self, mock_get):
        """Simula una caída total del internet durante la petición."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Sin conexión")

        resultado = self.recolector.obtener_detalle_licitacion("1111-22-L124")

        self.assertEqual(resultado['estado'], 'error_red')

if __name__ == "__main__":
    unittest.main()