"""
Módulo de instancias compartidas (Singleton por módulo).

En Python, los módulos se importan una sola vez y su estado persiste durante
toda la ejecución. Este archivo aprovecha ese comportamiento para garantizar
que exista una única instancia de la CalculadoraPuntajes en toda la aplicación.

¿Por qué es necesario?
    Si cada clase creara su propia instancia de CalculadoraPuntajes, al recargar
    las reglas en una instancia, las demás seguirían con las reglas viejas en
    memoria. Al centralizar aquí la instancia, todos los módulos que la importan
    están trabajando con exactamente el mismo objeto en RAM.

Uso:
    from src.services.instancias import calculadora_compartida
    
    # Para evaluar:
    puntaje, motivos = calculadora_compartida.evaluar_titulo("Licitación X")
    
    # Para recargar tras modificar reglas en la BD:
    calculadora_compartida.cargar_reglas_negocio()
"""

from src.services.calculadora import CalculadoraPuntajes

# Instancia única que vivirá durante todo el ciclo de vida de la aplicación.
# Se inicializa al importar este módulo por primera vez (al arrancar la app),
# cargando todas las reglas de negocio desde la base de datos.
calculadora_compartida = CalculadoraPuntajes()