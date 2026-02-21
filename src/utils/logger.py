import sys
import logging
from pathlib import Path

DIRECTORIO_RAIZ = Path(__file__).resolve().parents[2]
DIRECTORIO_LOGS = DIRECTORIO_RAIZ / "data" / "logs"

def inicializar_sistema_logs():
    """Configura los manejadores principales de registro (Archivo y Consola)."""
    DIRECTORIO_LOGS.mkdir(parents=True, exist_ok=True)
    archivo_log = DIRECTORIO_LOGS / "app.log"
    formato_estandar_log = "%(asctime)s - %(levelname)-8s - %(name)-15s - %(message)s"

    logging.basicConfig(
        level=logging.DEBUG,
        format=formato_estandar_log,
        filename=archivo_log,
        filemode="a",
        encoding="utf-8"
    )

    manejador_consola = logging.StreamHandler(sys.stdout)
    manejador_consola.setLevel(logging.INFO) 
    formateador_consola = logging.Formatter(formato_estandar_log)
    manejador_consola.setFormatter(formateador_consola)

    logging.getLogger().addHandler(manejador_consola)

def configurar_logger(nombre_modulo: str) -> logging.Logger:
    """Instancia un logger específico para un módulo."""
    return logging.getLogger(nombre_modulo)