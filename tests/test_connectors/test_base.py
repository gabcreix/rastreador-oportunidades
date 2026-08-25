from app.models import EstadoProcesamiento, Fuente
from app.pipeline.ingesta.base import ItemCapturado, guardar_capturas


def test_guardar_capturas_deduplica_por_url(session):
    fuente = Fuente(nombre="Test", tipo="foro", config_acceso="{}")
    session.add(fuente)
    session.commit()

    items = [
        ItemCapturado(url_original="https://example.com/1", contenido_bruto="a"),
        ItemCapturado(url_original="https://example.com/2", contenido_bruto="b"),
    ]

    nuevas = guardar_capturas(session, fuente, items)
    assert nuevas == 2
    assert fuente.fecha_ultimo_rastreo is not None

    # Repetir con un ítem ya visto y uno nuevo: solo debe entrar el nuevo.
    items_repetidos = items + [ItemCapturado(url_original="https://example.com/3", contenido_bruto="c")]
    nuevas_segunda_vez = guardar_capturas(session, fuente, items_repetidos)

    assert nuevas_segunda_vez == 1
    assert len(fuente.capturas) == 3
    assert all(c.estado_procesamiento == EstadoProcesamiento.PENDIENTE for c in fuente.capturas)
