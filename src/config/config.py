import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Determinación dinámica de la ruta raíz del proyecto.
# Si la aplicación está congelada (ej. compilada con PyInstaller), sys.frozen será True.
# De lo contrario, se retroceden tres niveles desde este archivo para llegar a la raíz.
if getattr(sys, 'frozen', False):
    DIRECTORIO_BASE = Path(sys.executable).resolve().parent
else:
    DIRECTORIO_BASE = Path(__file__).resolve().parent.parent.parent

# Ruta absoluta al archivo de variables de entorno
ruta_archivo_env = DIRECTORIO_BASE / ".env"

# Carga de las variables de entorno al sistema
# Se especifica utf-8 para evitar problemas con caracteres especiales en contraseñas
load_dotenv(ruta_archivo_env, encoding="utf-8")

# Extracción de variables críticas para el funcionamiento de la aplicación
DATABASE_URL = os.getenv("DATABASE_URL")
TICKET_MERCADO_PUBLICO = os.getenv("TICKET_MERCADO_PUBLICO")

# Validación estricta de configuración inicial.
# La aplicación no debe arrancar si faltan estas credenciales esenciales.
if not DATABASE_URL:
    raise ValueError(
        f"[CRITICAL] La variable DATABASE_URL no está configurada. "
        f"Verifique el archivo .env en: {ruta_archivo_env}"
    )

if not TICKET_MERCADO_PUBLICO:
    raise ValueError(
        f"[CRITICAL] La variable TICKET_MERCADO_PUBLICO no está configurada. "
        f"Verifique el archivo .env en: {ruta_archivo_env}"
    )