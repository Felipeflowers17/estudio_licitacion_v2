import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.bd.database import Base
from src.bd.models import Licitacion, EstadoLicitacion, Organismo
from src.repositories.licitaciones_repository import RepositorioLicitaciones
from src.config.constantes import EtapaLicitacion, ESTADO_LICITACION_ACTIVA

class TestRepositorioLicitaciones(unittest.TestCase):
    """
    Test de integración para la capa de persistencia.
    Utiliza una base de datos SQLite en memoria para validar las consultas.
    """

    def setUp(self):
        """
        Configura un entorno de base de datos aislado para cada test.
        """
        # 1. Crear motor SQLite en memoria
        self.engine = create_engine("sqlite:///:memory:")
        
        # 2. Crear las tablas basadas en tus modelos de SQLAlchemy
        Base.metadata.create_all(self.engine)
        
        # 3. Configurar la fábrica de sesiones para este motor de prueba
        self.TestingSessionLocal = sessionmaker(bind=self.engine)
        
        # 4. Instanciar el repositorio inyectando la sesión de pruebas
        self.repo = RepositorioLicitaciones(session_factory=self.TestingSessionLocal)
        
        # 5. Poblar con datos mínimos necesarios (Seed de prueba)
        self._preparar_datos_prueba()

    def _preparar_datos_prueba(self):
        """Inserta registros semilla para validar las consultas del repositorio."""
        with self.TestingSessionLocal() as sesion:
            # Crear estado activo
            estado_activo = EstadoLicitacion(codigo=ESTADO_LICITACION_ACTIVA, descripcion="Publicada")
            sesion.add(estado_activo)
            
            # Crear licitación candidata
            lic1 = Licitacion(
                codigo_externo="TEST-01",
                nombre="Licitación de Prueba 1",
                puntaje=50,
                etapa=EtapaLicitacion.CANDIDATA.value,
                codigo_estado=ESTADO_LICITACION_ACTIVA
            )
            
            # Crear licitación en seguimiento
            lic2 = Licitacion(
                codigo_externo="TEST-02",
                nombre="Licitación de Prueba 2",
                puntaje=80,
                etapa=EtapaLicitacion.SEGUIMIENTO.value,
                codigo_estado=ESTADO_LICITACION_ACTIVA
            )
            
            sesion.add_all([lic1, lic2])
            sesion.commit()

    def test_obtener_candidatas_paginadas(self):
        """Valida que el repositorio recupere solo las licitaciones en etapa candidata."""
        # En nuestro setUp solo insertamos 1 candidata (TEST-01)
        resultados = self.repo.obtener_candidatas(limit=10, offset=0)
        
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0].codigo_externo, "TEST-01")

    def test_mover_licitacion_exitoso(self):
        """Verifica que el cambio de etapa en la base de datos sea efectivo."""
        codigo = "TEST-01"
        nueva_etapa = EtapaLicitacion.SEGUIMIENTO.value
        
        exito = self.repo.mover_licitacion(codigo, nueva_etapa)
        
        self.assertTrue(exito)
        
        # Verificamos que realmente cambió en la BD
        with self.TestingSessionLocal() as sesion:
            lic = sesion.query(Licitacion).filter_by(codigo_externo=codigo).first()
            self.assertEqual(lic.etapa, nueva_etapa)

    def test_obtener_licitacion_inexistente(self):
        """Asegura que el repositorio maneje correctamente códigos que no están en la BD."""
        resultado = self.repo.obtener_licitacion_por_codigo("CODIGO-FALSO")
        self.assertIsNone(resultado)

    def tearDown(self):
        """Limpia los recursos después de cada test."""
        Base.metadata.drop_all(self.engine)

if __name__ == "__main__":
    unittest.main()