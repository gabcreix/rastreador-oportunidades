from sqlmodel import select

from app.models import Fuente, Perfil
from scripts.seed import AREAS_PERFIL, seed


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
