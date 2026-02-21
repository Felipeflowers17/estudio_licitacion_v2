import unittest
from unittest.mock import MagicMock, patch
from src.services.calculadora import CalculadoraPuntajes
from src.bd.models import PalabraClave, Organismo


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

        self.assertEqual(len(calc.reglas_en_memoria), 2, "Debería haber cargado 2 reglas")
        print("\n✅ Test de Carga de Reglas: PASADO")

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
        print("✅ Test de Evaluación de Título: PASADO")

    @patch('src.services.calculadora.SessionLocal')
    def test_evaluar_detalle_organismo(self, mock_session_local):
        """
        Probamos que sume puntos si el organismo es VIP.
        
        Corrección respecto a la versión anterior:
        Se usa side_effect para separar la respuesta de .all() (palabras clave)
        de la respuesta de .filter_by().first() (organismo). De esta forma,
        ambas llamadas a query() son independientes y el test es robusto.
        """
        organismo_falso = Organismo(codigo="ORG-123", nombre="Muni Test", puntaje=100)

        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)

        # Separamos las dos consultas distintas que hace evaluar_detalle:
        # - Primera llamada a query(): retorna las palabras clave via .all()
        # - Segunda llamada a query(): retorna el organismo via .filter_by().first()
        mock_query_palabras = MagicMock()
        mock_query_palabras.all.return_value = self.datos_falsos_bd

        mock_query_organismo = MagicMock()
        mock_query_organismo.filter_by.return_value.first.return_value = organismo_falso

        # side_effect hace que cada llamada consecutiva a query() use el siguiente valor
        mock_db.query.side_effect = [mock_query_palabras, mock_query_organismo]

        mock_session_local.return_value = mock_db

        calc = CalculadoraPuntajes()

        puntaje, motivos = calc.evaluar_detalle("ORG-123", "", "")

        self.assertEqual(puntaje, 100, "El puntaje debió ser 100 por el organismo")
        self.assertIn("Muni Test", motivos[0])
        print("✅ Test de Organismo: PASADO")

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
        print("✅ Test Mayúsculas/Minúsculas: PASADO")

    @patch('src.services.calculadora.SessionLocal')
    def test_manejo_valores_nulos(self, mock_session_local):
        """
        Prueba crítica: ¿Qué pasa si la descripción es None?
        La app NO debe crashear.
        """
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)

        # Para este test no hay organismo, la segunda query retorna None
        mock_query_palabras = MagicMock()
        mock_query_palabras.all.return_value = self.datos_falsos_bd

        mock_query_organismo = MagicMock()
        mock_query_organismo.filter_by.return_value.first.return_value = None

        mock_db.query.side_effect = [mock_query_palabras, mock_query_organismo]
        mock_session_local.return_value = mock_db

        calc = CalculadoraPuntajes()

        try:
            puntaje, motivos = calc.evaluar_detalle("ORG-XYZ", None, None)
            self.assertEqual(puntaje, 0)
            self.assertEqual(motivos, [])
            print("✅ Test Valores Nulos (None): PASADO")
        except AttributeError:
            self.fail("La calculadora falló al recibir None (posible error de .lower() en un NoneType)")


if __name__ == '__main__':
    unittest.main()