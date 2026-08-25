import json

import pytest

from app.models import Fuente
from app.pipeline.fuentes import NOMBRE_APPLE, NOMBRE_GOOGLE_NEWS, NOMBRE_HACKERNEWS, NOMBRE_REDDIT_IDEAS
from app.pipeline.ingesta.apple_appstore import ConectorAppleAppStore
from app.pipeline.ingesta.factory import crear_conector
from app.pipeline.ingesta.google_news import ConectorGoogleNews
from app.pipeline.ingesta.rss import ConectorRSS


def _fuente(nombre: str, config: dict) -> Fuente:
    return Fuente(nombre=nombre, tipo="x", config_acceso=json.dumps(config))


def test_factory_hackernews_da_conector_rss():
    conector = crear_conector(_fuente(NOMBRE_HACKERNEWS, {"urls": ["https://hnrss.org/ask"]}))
    assert isinstance(conector, ConectorRSS)


def test_factory_google_news_da_conector_google_news():
    conector = crear_conector(_fuente(NOMBRE_GOOGLE_NEWS, {"consultas": ["fintech"]}))
    assert isinstance(conector, ConectorGoogleNews)


def test_factory_apple_da_conector_apple():
    conector = crear_conector(_fuente(NOMBRE_APPLE, {"app_ids": ["1"], "paises": ["es"]}))
    assert isinstance(conector, ConectorAppleAppStore)


def test_factory_reddit_no_implementado_todavia():
    with pytest.raises(NotImplementedError):
        crear_conector(_fuente(NOMBRE_REDDIT_IDEAS, {"urls": ["https://reddit.com/x.rss"]}))


def test_factory_fuente_desconocida():
    with pytest.raises(ValueError):
        crear_conector(_fuente("Fuente rara", {}))
