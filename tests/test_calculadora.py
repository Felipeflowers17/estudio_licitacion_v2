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
        # 1. Creamos reglas falsas (Palabras Clave)
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
        
        # Esta lista simulará ser nuestra tabla de base de datos
        self.datos_falsos_bd = [self.regla_silla, self.regla_mesa]

    @patch('src.services.calculadora.SessionLocal')
    def test_carga_reglas(self, mock_session_local):
        """
        Probamos que la calculadora cargue correctamente las reglas al iniciar.
        """
        # Configuramos el Mock de la sesión para que devuelva nuestra lista falsa
        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = self.datos_falsos_bd
        mock_session_local.return_value = mock_db

        # Instanciamos la calculadora (esto llamará a cargar_reglas internamente)
        calc = CalculadoraPuntajes()

        # Verificamos
        self.assertEqual(len(calc.reglas_en_memoria), 2, "Debería haber cargado 2 reglas")
        print("\n✅ Test de Carga de Reglas: PASADO")

    @patch('src.services.calculadora.SessionLocal')
    def test_evaluar_titulo(self, mock_session_local):
        """
        Probamos la lógica de suma de puntos en el Título.
        Caso: Un título que tiene "Silla" y "Mesa".
        Esperado: 10 + 20 = 30 puntos.
        """
        # Configuración del Mock (Igual que arriba)
        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = self.datos_falsos_bd
        mock_session_local.return_value = mock_db

        calc = CalculadoraPuntajes()

        # EJECUCIÓN
        titulo_prueba = "Licitación para compra de Silla y Mesa de oficina"
        puntaje, motivos = calc.evaluar_titulo(titulo_prueba)

        # VERIFICACIÓN
        self.assertEqual(puntaje, 30, f"El puntaje debió ser 30, fue {puntaje}")
        self.assertTrue(any("Silla" in m for m in motivos))
        self.assertTrue(any("Mesa" in m for m in motivos))
        print("✅ Test de Evaluación de Título: PASADO")

    @patch('src.services.calculadora.SessionLocal')
    def test_evaluar_detalle_organismo(self, mock_session_local):
        """
        Probamos que sume puntos si el organismo es VIP.
        """
        # 1. Simulamos las reglas de palabras
        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = self.datos_falsos_bd
        
        # 2. Simulamos la consulta del Organismo
        # Cuando busque un organismo, devolveremos uno falso con 100 puntos
        organismo_falso = Organismo(codigo="ORG-123", nombre="Muni Test", puntaje=100)
        mock_db.query.return_value.filter_by.return_value.first.return_value = organismo_falso
        
        mock_session_local.return_value = mock_db

        calc = CalculadoraPuntajes()

        # EJECUCIÓN
        # Pasamos un código de organismo, y descripciones vacías para aislar el test
        puntaje, motivos = calc.evaluar_detalle("ORG-123", "", "")

        # VERIFICACIÓN
        self.assertEqual(puntaje, 100, "El puntaje debió ser 100 por el organismo")
        self.assertIn("Muni Test", motivos[0])
        print("✅ Test de Organismo: PASADO")

    @patch('src.services.calculadora.SessionLocal')
    def test_insensibilidad_mayusculas(self, mock_session_local):
        """
        Prueba que 'Silla' sea detectado igual que 'siLLa' o 'SILLA'.
        """
        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = self.datos_falsos_bd
        mock_session_local.return_value = mock_db
        
        calc = CalculadoraPuntajes()
        
        # El título está en mayúsculas, pero la regla es "Silla" (Capitalizada)
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
        mock_db.query.return_value.all.return_value = self.datos_falsos_bd
        mock_session_local.return_value = mock_db
        
        calc = CalculadoraPuntajes()
        
        # Pasamos None en descripción y productos
        try:
            puntaje, motivos = calc.evaluar_detalle("ORG-XYZ", None, None)
            # Si llegamos aquí sin error, pasó la prueba de humo
            self.assertEqual(puntaje, 0)
            self.assertEqual(motivos, [])
            print("✅ Test Valores Nulos (None): PASADO")
        except AttributeError:
            self.fail("La calculadora falló al recibir None (posible error de .lower() en un NoneType)")

if __name__ == '__main__':
    unittest.main()