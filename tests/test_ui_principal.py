import pytest
from PySide6.QtCore import Qt
from src.UI.ventana_principal import VentanaPrincipal

@pytest.fixture
def app(qtbot):
    """
    Fixture que instancia la ventana principal y la registra en qtbot.
    """
    ventana = VentanaPrincipal()
    qtbot.addWidget(ventana)
    return ventana

def test_navegacion_menu_lateral(app, qtbot):
    """
    Verifica que al seleccionar elementos en el menú lateral,
    el QStackedWidget cambie a la página correspondiente.
    """
    # 1. Comprobamos estado inicial (Pestaña Candidatas - Índice 0)
    assert app.pila_vistas.currentIndex() == 0

    # 2. Simulamos clic en la opción 'Herramientas' (Índice 3 en tu QListWidget)
    item_herramientas = app.lista_menu.item(3)
    rect = app.lista_menu.visualItemRect(item_herramientas)

    # qtbot hace el clic físico en el viewport de la lista
    qtbot.mouseClick(app.lista_menu.viewport(), Qt.LeftButton, pos=rect.center())

    # 3. Verificamos que la página cambió en el QStackedWidget
    # Usamos currentIndex que es el estándar de Qt para verificar navegación
    assert app.pila_vistas.currentIndex() == 3

def test_existencia_componentes_clave(app):
    """
    Asegura que los widgets críticos se hayan instanciado con los nombres correctos.
    """
    assert hasattr(app, 'vista_candidatas')
    assert hasattr(app, 'vista_seguimiento')
    assert hasattr(app, 'vista_herramientas')
    assert app.lista_menu.count() == 4

def test_marcar_desactualizado_global(app):
    """
    Prueba que la función de refresco global 'ensucie' las banderas
    de todas las pestañas usando el método real de tu clase.
    """
    # Ponemos las banderas en False manualmente para probar el cambio
    app.vista_candidatas.necesita_actualizacion = False
    app.vista_seguimiento.necesita_actualizacion = False

    # Ejecutamos el método real según tu archivo ventana_principal.py
    app.marcar_vistas_como_desactualizadas()
    
    # Verificamos que se marcaron como True (Dirty Flag)
    assert app.vista_candidatas.necesita_actualizacion is True
    assert app.vista_seguimiento.necesita_actualizacion is True