import json

from app.models import Fuente
from app.pipeline.fuentes import (
    NOMBRE_APPLE,
    NOMBRE_GOOGLE_NEWS,
    NOMBRE_HACKERNEWS,
    NOMBRE_PRENSA,
    NOMBRE_PRODUCT_HUNT,
    NOMBRE_REDDIT_IDEAS,
    NOMBRE_REDDIT_NEGOCIO,
)
from app.pipeline.ingesta.apple_appstore import ConectorAppleAppStore
from app.pipeline.ingesta.base import Conector
from app.pipeline.ingesta.google_news import ConectorGoogleNews
from app.pipeline.ingesta.reddit import ConectorReddit
from app.pipeline.ingesta.rss import ConectorRSS

FUENTES_RSS_SIMPLES = {NOMBRE_HACKERNEWS, NOMBRE_PRODUCT_HUNT, NOMBRE_PRENSA}
FUENTES_REDDIT = {NOMBRE_REDDIT_IDEAS, NOMBRE_REDDIT_NEGOCIO}


def crear_conector(fuente: Fuente) -> Conector:
    config = json.loads(fuente.config_acceso)

    if fuente.nombre in FUENTES_RSS_SIMPLES:
        return ConectorRSS(config["urls"])

    if fuente.nombre == NOMBRE_GOOGLE_NEWS:
        return ConectorGoogleNews(config["consultas"])

    if fuente.nombre == NOMBRE_APPLE:
        return ConectorAppleAppStore(
            paises_charts=config["paises_charts"],
            tipos_chart=config["tipos_chart"],
            limite_chart=config["limite_chart"],
            generos_interes=config["generos_interes"],
            paises_resenas=config["paises_resenas"],
            paginas_resenas=config.get("paginas_resenas", 2),
        )

    if fuente.nombre in FUENTES_REDDIT:
        return ConectorReddit(urls_new=config["urls"], consultas=config.get("consultas", []))

    raise ValueError(f"No hay conector definido para la fuente {fuente.nombre!r}")
