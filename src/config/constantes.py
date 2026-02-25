"""
Archivo centralizado de constantes y reglas de negocio globales.
Evita el uso de 'Magic Numbers' y 'Magic Strings' en el código fuente, 
facilitando la configuración y mantenimiento del sistema.
"""
from enum import Enum

# Definición de las Etapas del Flujo de Licitaciones
class EtapaLicitacion(Enum):
    CANDIDATA = "candidata"
    SEGUIMIENTO = "seguimiento"
    OFERTADA = "ofertada"
    IGNORADA = "ignorada"

# Estados de Licitación (API Mercado Público)
ESTADO_LICITACION_ACTIVA = 5

# Límites de visualización y consulta
LIMITE_LICITACIONES_ACTIVAS = 200
LIMITE_CANDIDATAS_VISIBLES = 1000

# Umbrales de evaluación
UMBRAL_PUNTAJE_CANDIDATA = 0

# Configuraciones de red y resiliencia
PAUSA_ENTRE_DIAS_EXTRACCION = 5  # Segundos

TAMANIO_PAGINA_TABLAS = 50

TAMANIO_CHUNK_EXPORTACION = 2000

# Resiliencia del Piloto Automático
PILOTO_MAX_REINTENTOS = 3
PILOTO_MINUTOS_REINTENTOS_BASE = 5

# Diccionario oficial de estados de Mercado Público
ESTADOS_MERCADO_PUBLICO = {
    5: "Publicada",
    6: "Cerrada",
    7: "Desierta",
    8: "Adjudicada",
    18: "Revocada",
    19: "Suspendida"
}