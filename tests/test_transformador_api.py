import unittest
from datetime import datetime, timezone
from src.services.transformador_api import TransformadorAPI

class TestTransformadorAPI(unittest.TestCase):
    """
    Suite de pruebas unitarias para validar la integridad de la transformación
    de datos crudos de la API de Mercado Público a tipos nativos de Python.
    """

    def setUp(self):
        """Prepara estructuras de datos de ejemplo basadas en la respuesta real de la API."""
        self.datos_api_completos = {
            "FechaCierre": "2024-03-20T15:00:00Z",
            "Fechas": {
                "FechaInicio": "2024-03-01T08:00:00Z",
                "FechaPublicacion": "2024-02-28T10:00:00Z",
                "FechaEstimadaAdjudicacion": "2024-04-10T18:00:00Z"
            },
            "Items": {
                "Listado": [
                    {
                        "NombreProducto": "Silla Ergonómica",
                        "Cantidad": 10,
                        "UnidadMedida": "Unidad",
                        "Descripcion": "Silla de oficina negra"
                    },
                    {
                        "NombreProducto": "Mesa de Escritorio",
                        "Cantidad": 2,
                        "UnidadMedida": "Unidad",
                        "Descripcion": "Mesa de madera"
                    }
                ]
            }
        }

    def test_parsear_fechas_exitoso(self):
        """Verifica que los strings ISO se conviertan correctamente a objetos datetime."""
        fechas = TransformadorAPI.parsear_fechas(self.datos_api_completos)
        
        # Comprobamos que sean objetos datetime
        self.assertIsInstance(fechas["cierre"], datetime)
        self.assertIsInstance(fechas["publicacion"], datetime)
        
        # Verificamos valores específicos
        self.assertEqual(fechas["cierre"].year, 2024)
        self.assertEqual(fechas["cierre"].month, 3)
        self.assertEqual(fechas["cierre"].day, 20)

    def test_parsear_fechas_nulas(self):
        """Verifica la robustez del sistema ante la ausencia de fechas."""
        datos_vacios = {"Fechas": {}}
        fechas = TransformadorAPI.parsear_fechas(datos_vacios)
        
        self.assertIsNone(fechas["cierre"])
        self.assertIsNone(fechas["inicio"])
        self.assertIsNone(fechas["adjudicacion"])

    def test_construir_texto_productos_formateado(self):
        """Valida que la lista de productos se convierta en un string legible y estructurado."""
        texto = TransformadorAPI.construir_texto_productos(self.datos_api_completos)
        
        self.assertIn("- Silla Ergonómica (10 Unidad)", texto)
        self.assertIn("Detalle: Silla de oficina negra", texto)
        self.assertIn("- Mesa de Escritorio (2 Unidad)", texto)

    def test_construir_texto_productos_vacio(self):
        """Asegura que el sistema no falle si la licitación no tiene ítems declarados."""
        datos_sin_items = {"Items": {"Listado": []}}
        texto = TransformadorAPI.construir_texto_productos(datos_sin_items)
        
        self.assertEqual(texto, "")

    def test_manejo_descripcion_redundante(self):
        """Verifica que no se repita la descripción si es idéntica al nombre del producto."""
        datos_redundantes = {
            "Items": [
                {
                    "NombreProducto": "Papel",
                    "Cantidad": 1,
                    "UnidadMedida": "Resma",
                    "Descripcion": "papel" # Es igual al nombre (en minúsculas)
                }
            ]
        }
        texto = TransformadorAPI.construir_texto_productos(datos_redundantes)
        
        self.assertIn("- Papel (1 Resma)", texto)
        self.assertNotIn("Detalle: papel", texto)

if __name__ == "__main__":
    unittest.main()