"""
Archivo centralizado de constantes y reglas de negocio globales.
Evita el uso de 'Magic Numbers' en el código fuente, facilitando
la configuración y mantenimiento del sistema.
"""

# Estados de Licitación (API Mercado Público)
ESTADO_LICITACION_ACTIVA = 5

# Límites de visualización y consulta
LIMITE_LICITACIONES_ACTIVAS = 200
LIMITE_CANDIDATAS_VISIBLES = 1000

# Umbrales de evaluación
UMBRAL_PUNTAJE_CANDIDATA = 0

# Configuraciones de red y resiliencia
PAUSA_ENTRE_DIAS_EXTRACCION = 5  # Segundos