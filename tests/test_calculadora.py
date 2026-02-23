import unittest
from unittest.mock import MagicMock, patch
from src.services.calculadora import CalculadoraPuntajes
from src.bd.models import PalabraClave


class TestCalculadoraPuntajes(unittest.TestCase):

    def setUp(self):
        """
        Este método se ejecuta ANTES de cada prueba.
        Aquí preparamos nuestros datos falsos (Mocks).
        """
        self.regla_silla = PalabraClave(
            palabra="Silla",
            puntaje_titulo=10,
            puntaje_descripcion=5,
            puntaje_productos=1
        )
        self.regla_mesa = PalabraClave(
            palabra="Mesa",
            puntaje_titulo=20,
            puntaje_descripcion=10,
            puntaje_productos=2
        )
        self.datos_falsos_bd = [self.regla_silla, self.regla_mesa]

    @patch('src.services.calculadora.SessionLocal')
    def test_carga_reglas(self, mock_session_local):
        """
        Probamos que la calculadora cargue correctamente las reglas al iniciar.
        """
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.all.return_value = self.datos_falsos_bd
        mock_session_local.return_value = mock_db

        calc = CalculadoraPuntajes()

        self.assertEqual(len(calc.reglas_compiladas), 2, "Debería haber cargado 2 reglas precompiladas")
        print("\nTest de Carga de Reglas: PASADO")

    @patch('src.services.calculadora.SessionLocal')
    def test_evaluar_titulo(self, mock_session_local):
        """
        Probamos la lógica de suma de puntos en el Título.
        Caso: Un título que tiene "Silla" y "Mesa".
        Esperado: 10 + 20 = 30 puntos.
        """
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.all.return_value = self.datos_falsos_bd
        mock_session_local.return_value = mock_db

        calc = CalculadoraPuntajes()

        titulo_prueba = "Licitación para compra de Silla y Mesa de oficina"
        puntaje, motivos = calc.evaluar_titulo(titulo_prueba)

        self.assertEqual(puntaje, 30, f"El puntaje debió ser 30, fue {puntaje}")
        self.assertTrue(any("Silla" in m for m in motivos))
        self.assertTrue(any("Mesa" in m for m in motivos))
        print("Test de Evaluación de Título: PASADO")

    @patch('src.services.calculadora.SessionLocal')
    def test_evaluar_detalle(self, mock_session_local):
        """
        Probamos que sume puntos correctamente al analizar descripciones y productos.
        La función ahora es pura y no depende de la base de datos de organismos.
        """
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.all.return_value = self.datos_falsos_bd
        mock_session_local.return_value = mock_db

        calc = CalculadoraPuntajes()

        # Evaluamos descripción con "Mesa" (10 pts) y producto con "Silla" (1 pt)
        puntaje, motivos = calc.evaluar_detalle(descripcion="Se requiere una Mesa amplia", texto_productos="Silla de madera")

        self.assertEqual(puntaje, 11, "El puntaje debió ser 11 (10 por mesa en desc, 1 por silla en prod)")
        self.assertTrue(any("Mesa" in m for m in motivos))
        self.assertTrue(any("Silla" in m for m in motivos))
        print("Test de Evaluación de Detalles Puros: PASADO")

    @patch('src.services.calculadora.SessionLocal')
    def test_insensibilidad_mayusculas(self, mock_session_local):
        """
        Prueba que 'Silla' sea detectado igual que 'siLLa' o 'SILLA'.
        """
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.all.return_value = self.datos_falsos_bd
        mock_session_local.return_value = mock_db

        calc = CalculadoraPuntajes()

        titulo = "COMPRA DE SILLA GAMER"
        puntaje, motivos = calc.evaluar_titulo(titulo)

        self.assertEqual(puntaje, 10, "No detectó la palabra en mayúsculas")
        print("Test Mayúsculas/Minúsculas: PASADO")

    @patch('src.services.calculadora.SessionLocal')
    def test_manejo_valores_nulos(self, mock_session_local):
        """
        Prueba crítica: ¿Qué pasa si la descripción es None?
        La app NO debe crashear.
        """
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.all.return_value = self.datos_falsos_bd
        mock_session_local.return_value = mock_db

        calc = CalculadoraPuntajes()

        try:
            puntaje, motivos = calc.evaluar_detalle(None, None)
            self.assertEqual(puntaje, 0)
            self.assertEqual(motivos, [])
            print("Test Valores Nulos (None): PASADO")
        except AttributeError:
            self.fail("La calculadora falló al recibir None (posible error de .lower() en un NoneType)")


if __name__ == '__main__':
    unittest.main()