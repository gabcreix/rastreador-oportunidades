import json

from sqlmodel import select

from app.models import Fuente, Perfil
from app.pipeline.fuentes import NOMBRE_HACKERNEWS
from scripts.seed import AREAS_PERFIL, FUENTES, seed


def test_seed_crea_perfil_areas_y_fuentes(session):
    seed(session)

    perfil = session.exec(select(Perfil)).one()
    assert perfil.retencion_dias == 30
    assert {area.nombre for area in perfil.areas} == set(AREAS_PERFIL)

    fuentes = session.exec(select(Fuente)).all()
    assert len(fuentes) == 7
    assert all(fuente.activa for fuente in fuentes)


def test_seed_es_idempotente(session):
    seed(session)
    seed(session)

    assert len(session.exec(select(Fuente)).all()) == 7
    assert len(session.exec(select(Perfil)).all()) == 1


def test_seed_sincroniza_config_acceso_si_cambia_en_codigo(session, monkeypatch):
    seed(session)

    nuevo_config = json.dumps({"urls": ["https://nuevo.example/feed"]})
    fuentes_modificadas = [
        {**f, "config_acceso": nuevo_config} if f["nombre"] == NOMBRE_HACKERNEWS else f
        for f in FUENTES
    ]
    monkeypatch.setattr("scripts.seed.FUENTES", fuentes_modificadas)

    seed(session)

    fuente = session.exec(select(Fuente).where(Fuente.nombre == NOMBRE_HACKERNEWS)).one()
    assert fuente.config_acceso == nuevo_config
    assert len(session.exec(select(Fuente)).all()) == 7
