import sys
from PySide6.QtWidgets import QApplication 
from src.utils.logger import inicializar_sistema_logs, configurar_logger
from src.config.config import DIRECTORIO_BASE, DATABASE_URL
from src.bd.database import engine
from src.UI.ventana_principal import VentanaPrincipal 

# Inicialización temprana del sistema de registro
inicializar_sistema_logs()
logger = configurar_logger("arranque_sistema")

def main():
    """
    Punto de entrada principal de la aplicación.
    """
    logger.info("[SISTEMA] Iniciando la secuencia de arranque de la aplicación...")
    logger.info(f"[SISTEMA] Directorio raíz detectado: {DIRECTORIO_BASE}")

    if DATABASE_URL:
        logger.info("[SISTEMA] Comprobando conexión con la base de datos...")
        try:
            # Solo verificamos conectividad. 
            # La creación de tablas queda delegada estrictamente a las migraciones de Alembic.
            with engine.connect() as conexion:
                logger.info("[SISTEMA] Conexión establecida correctamente con PostgreSQL.")
        except Exception as error_bd:
            logger.error(f"[CRITICAL] Falla crítica al conectar con la base de datos: {error_bd}")
            sys.exit(1)
    else:
        logger.error("[CRITICAL] La variable DATABASE_URL no se encuentra configurada en el entorno.")
        sys.exit(1)
    
    logger.info("[SISTEMA] Inicializando el entorno visual...")
    aplicacion = QApplication(sys.argv)
    aplicacion.setStyle("Fusion") 

    ventana_base = VentanaPrincipal()
    ventana_base.show()
    
    logger.info("[SISTEMA] Interfaz gráfica desplegada. Cediendo control al usuario.")
    sys.exit(aplicacion.exec())

if __name__ == "__main__":
    main()