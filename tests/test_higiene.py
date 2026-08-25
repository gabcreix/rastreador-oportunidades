from datetime import datetime, timedelta

from sqlmodel import select

from app.models import Captura, EstadoProcesamiento, Fuente
from app.pipeline.higiene import (
    es_contenido_vacio_o_roto,
    es_idioma_fuera_de_alcance,
    es_spam_evidente,
    hash_contenido,
    procesar_capturas_pendientes,
)


def test_contenido_vacio_o_roto():
    assert es_contenido_vacio_o_roto("")
    assert es_contenido_vacio_o_roto("   ")
    assert es_contenido_vacio_o_roto("corto")
    assert not es_contenido_vacio_o_roto(
        "Este es un contenido con longitud suficiente para pasar el filtro."
    )


def test_spam_evidente():
    assert es_spam_evidente("¡CLICK HERE TO CLAIM tu premio ahora!")
    assert es_spam_evidente("Ganaste un premio %s" % ("!" * 12))
    assert not es_spam_evidente(
        "Alguien pregunta si existe una app para gestionar gastos compartidos."
    )


def test_idioma_fuera_de_alcance():
    assert es_idioma_fuera_de_alcance(
        "Ceci est un article de presse en français à propos d'une nouvelle réglementation."
    )
    assert not es_idioma_fuera_de_alcance(
        "Este es un artículo de prensa en español sobre una nueva normativa fiscal para autónomos."
    )
    assert not es_idioma_fuera_de_alcance(
        "This is a news article in English about a new regulation for small businesses."
    )
    # Sin texto suficiente para detectar nada: alto recall, se deja pasar.
    assert not es_idioma_fuera_de_alcance("")


def test_hash_contenido_ignora_mayusculas_y_espacios():
    assert hash_contenido("Hola   Mundo") == hash_contenido("hola mundo")
    assert hash_contenido("Hola Mundo") != hash_contenido("Adiós Mundo")


def _crear_captura(session, fuente, contenido, url, fecha):
    captura = Captura(fuente_id=fuente.id, contenido_bruto=contenido, url_original=url, fecha_captura=fecha)
    session.add(captura)
    session.commit()
    return captura


def test_procesar_capturas_pendientes_clasifica_correctamente(session):
    fuente = Fuente(nombre="Test", tipo="prensa", config_acceso="{}")
    session.add(fuente)
    session.commit()

    base = datetime(2026, 1, 1)
    normal = _crear_captura(
        session,
        fuente,
        "Alguien pregunta si existe una app para gestionar gastos compartidos entre amigos.",
        "https://example.com/1",
        base,
    )
    duplicado = _crear_captura(
        session,
        fuente,
        "alguien   pregunta si existe una app para gestionar gastos compartidos entre amigos.",
        "https://example.com/2",
        base + timedelta(seconds=1),
    )
    vacio = _crear_captura(session, fuente, "   ", "https://example.com/3", base + timedelta(seconds=2))
    spam = _crear_captura(
        session,
        fuente,
        "CLICK HERE TO CLAIM tu premio ya mismo",
        "https://example.com/4",
        base + timedelta(seconds=3),
    )
    frances = _crear_captura(
        session,
        fuente,
        "Ceci est un article de presse en français à propos d'une nouvelle réglementation.",
        "https://example.com/5",
        base + timedelta(seconds=4),
    )

    contadores = procesar_capturas_pendientes(session)

    for captura in (normal, duplicado, vacio, spam, frances):
        session.refresh(captura)

    assert normal.estado_procesamiento == EstadoProcesamiento.PROCESADA
    assert duplicado.estado_procesamiento == EstadoProcesamiento.DESCARTADA
    assert vacio.estado_procesamiento == EstadoProcesamiento.DESCARTADA
    assert spam.estado_procesamiento == EstadoProcesamiento.DESCARTADA
    assert frances.estado_procesamiento == EstadoProcesamiento.DESCARTADA

    assert contadores == {"procesada": 1, "descartada": 4}

    # Nada se borra: las 5 Capturas siguen existiendo, solo cambia su estado.
    assert len(session.exec(select(Captura)).all()) == 5


def test_procesar_capturas_pendientes_es_idempotente(session):
    fuente = Fuente(nombre="Test", tipo="prensa", config_acceso="{}")
    session.add(fuente)
    session.commit()

    _crear_captura(session, fuente, "Un contenido normal y suficientemente largo.", "https://example.com/1", datetime(2026, 1, 1))

    primera = procesar_capturas_pendientes(session)
    segunda = procesar_capturas_pendientes(session)

    assert primera == {"procesada": 1, "descartada": 0}
    assert segunda == {"procesada": 0, "descartada": 0}
