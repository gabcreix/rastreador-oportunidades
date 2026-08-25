from app.models import (
    AccionFeedback,
    Area,
    CapaDeteccion,
    Captura,
    EstadoOportunidad,
    EstadoProcesamiento,
    EventoFeedback,
    Fuente,
    Oportunidad,
    TipoOportunidad,
)


def _crear_captura(session, url="https://example.com/1"):
    fuente = Fuente(nombre="Test", tipo="foro", config_acceso="{}")
    session.add(fuente)
    session.commit()

    captura = Captura(
        fuente_id=fuente.id,
        contenido_bruto="texto bruto",
        url_original=url,
        estado_procesamiento=EstadoProcesamiento.PENDIENTE,
    )
    session.add(captura)
    session.commit()
    return fuente, captura


def test_captura_pertenece_a_fuente(session):
    fuente, captura = _crear_captura(session)

    assert captura.fuente.nombre == "Test"
    assert fuente.capturas[0].id == captura.id


def test_oportunidad_deriva_fuente_via_captura_y_nace_nueva(session):
    fuente, captura = _crear_captura(session, url="https://example.com/2")

    area = Area(nombre="software")
    session.add(area)
    session.commit()

    oportunidad = Oportunidad(
        titulo="Una oportunidad",
        descripcion="Un hueco detectado",
        tipo=TipoOportunidad.HUECO,
        capa=CapaDeteccion.INFERIDA,
        captura_origen_id=captura.id,
    )
    oportunidad.areas.append(area)
    session.add(oportunidad)
    session.commit()

    assert oportunidad.estado == EstadoOportunidad.NUEVA
    assert oportunidad.captura_origen.fuente.nombre == fuente.nombre
    assert area.oportunidades[0].id == oportunidad.id


def test_evento_feedback_queda_ligado_a_la_oportunidad(session):
    _, captura = _crear_captura(session, url="https://example.com/3")

    oportunidad = Oportunidad(
        titulo="t",
        descripcion="d",
        tipo=TipoOportunidad.MEJORAR,
        capa=CapaDeteccion.EXPLICITA,
        captura_origen_id=captura.id,
    )
    session.add(oportunidad)
    session.commit()

    evento = EventoFeedback(
        oportunidad_id=oportunidad.id,
        accion=AccionFeedback.GUARDAR,
        estado_resultante=EstadoOportunidad.GUARDADA.value,
    )
    session.add(evento)
    session.commit()

    assert oportunidad.eventos[0].accion == AccionFeedback.GUARDAR
