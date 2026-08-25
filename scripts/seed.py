"""Crea el Perfil único inicial, sus Áreas y las 7 Fuentes de arranque del MVP.

Idempotente: se puede ejecutar varias veces sin duplicar filas.
Uso: python -m scripts.seed
"""

import json

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Area, Fuente, Perfil
from app.pipeline.fuentes import (
    NOMBRE_APPLE,
    NOMBRE_GOOGLE_NEWS,
    NOMBRE_HACKERNEWS,
    NOMBRE_PRENSA,
    NOMBRE_PRODUCT_HUNT,
    NOMBRE_REDDIT_IDEAS,
    NOMBRE_REDDIT_NEGOCIO,
)

AREAS_PERFIL = [
    "software",
    "ingeniería de datos",
    "deportes",
    "finanzas",
    "aficiones",
    "cine",
    "literatura",
]

# config_acceso guarda siempre JSON con, como mínimo, la clave "urls" (lista de
# feeds RSS que agrega esa Fuente). Apple y Google News llevan además claves
# propias (app_ids/países, consultas) todavía vacías: se rellenan en la Fase 2
# de conectores, cuando Gabriel elija las apps a vigilar y las consultas.
# Catálogo de consultas de arranque (07-estrategia-consultas.md §6.1): 3 de
# Reddit + 4 de Google News. E-RD-01/03 son globales (no atadas a un
# subreddit) y se cuelgan de la Fuente "ideas"; E-RD-06 está acotada a los
# subs de negocio/SaaS (+ startups) y se cuelga de esa Fuente.
_CONSULTAS_REDDIT_IDEAS = [
    {
        "id": "E-RD-01",
        "q": '("someone should build" OR "is there an app that" OR "why is there no" '
        'OR "app that doesn\'t exist") self:true',
        "scope": "global",
    },
    {
        "id": "E-RD-03",
        "q": '("alternative to" OR "sick of" OR "tired of" OR "there has to be a better way") self:true',
        "scope": "global",
    },
]

_CONSULTAS_REDDIT_NEGOCIO = [
    {
        "id": "E-RD-06",
        "q": '("looking for a tool" OR "is there an app" OR "alternative to" OR "biggest pain point")',
        "scope": "subreddit",
        "subs": "SaaS+Entrepreneur+smallbusiness+startups",
    },
]

_CONSULTAS_GOOGLE_NEWS = [
    {
        "id": "I-GN-A1",
        "q": '"ingeniería de datos" OR "data engineering" OR "data pipeline" when:14d',
        "idiomas": ["es-ES", "en-US"],
    },
    {
        "id": "I-GN-A2",
        "q": 'fintech OR "banca digital" OR neobanco OR "pagos digitales" when:14d',
        "idiomas": ["es-ES", "en-US"],
    },
    {
        "id": "I-GN-B1",
        "q": "intitle:(normativa OR regulación OR ley OR reglamento) (pymes OR autónomos OR empresas) when:30d",
        "idiomas": ["es-ES"],
    },
    {
        "id": "E-GN-01",
        "q": '("no existe una app" OR "falta una plataforma" OR "necesitamos una herramienta" '
        'OR "nadie ha creado") when:30d',
        "idiomas": ["es-ES"],
    },
]

FUENTES = [
    {
        "nombre": NOMBRE_REDDIT_IDEAS,
        "tipo": "foro",
        "config_acceso": json.dumps(
            {
                "urls": ["https://www.reddit.com/r/SomebodyMakeThis+AppIdeas+Lightbulb/new.rss"],
                "consultas": _CONSULTAS_REDDIT_IDEAS,
            }
        ),
    },
    {
        "nombre": NOMBRE_REDDIT_NEGOCIO,
        "tipo": "foro",
        "config_acceso": json.dumps(
            {
                "urls": ["https://www.reddit.com/r/SaaS+Entrepreneur+smallbusiness/new.rss"],
                "consultas": _CONSULTAS_REDDIT_NEGOCIO,
            }
        ),
    },
    {
        "nombre": NOMBRE_HACKERNEWS,
        "tipo": "foro",
        "config_acceso": json.dumps({"urls": ["https://hnrss.org/ask", "https://hnrss.org/show"]}),
    },
    {
        "nombre": NOMBRE_APPLE,
        "tipo": "reseñas",
        # Descubrimiento por top charts (07-estrategia-consultas.md §8), no watchlist.
        "config_acceso": json.dumps(
            {
                "paises_charts": ["us", "es"],
                "tipos_chart": ["top-free", "top-paid"],
                "limite_chart": 50,
                "generos_interes": ["6015", "6000", "6007", "6026", "6002"],
                "paises_resenas": ["es", "us"],
                "paginas_resenas": 2,
            }
        ),
    },
    {
        "nombre": NOMBRE_GOOGLE_NEWS,
        "tipo": "búsquedas",
        "config_acceso": json.dumps({"consultas": _CONSULTAS_GOOGLE_NEWS}),
    },
    {
        "nombre": NOMBRE_PRENSA,
        "tipo": "prensa",
        "config_acceso": json.dumps(
            {"urls": ["https://techcrunch.com/feed/", "https://www.xataka.com/index.xml"]}
        ),
    },
    {
        "nombre": NOMBRE_PRODUCT_HUNT,
        "tipo": "lanzamientos",
        "config_acceso": json.dumps({"urls": ["https://www.producthunt.com/feed"]}),
    },
]


def seed(session: Session) -> None:
    areas_por_nombre = {}
    for nombre in AREAS_PERFIL:
        area = session.exec(select(Area).where(Area.nombre == nombre)).first()
        if area is None:
            area = Area(nombre=nombre)
            session.add(area)
            session.flush()
        areas_por_nombre[nombre] = area

    if session.exec(select(Perfil)).first() is None:
        perfil = Perfil(
            skills="ingeniería informática, ingeniería de datos, cine",
            pref_esfuerzo="manejable, no es una gran restricción",
            pref_capital="menor necesidad de capital = punto a favor",
            retencion_dias=30,
        )
        perfil.areas = list(areas_por_nombre.values())
        session.add(perfil)

    for datos in FUENTES:
        existente = session.exec(select(Fuente).where(Fuente.nombre == datos["nombre"])).first()
        if existente is None:
            session.add(Fuente(activa=True, **datos))
        else:
            # Las fuentes se definen en código (F8 · gestión de fuentes es post-MVP):
            # el código manda, así que cada re-siembra sincroniza tipo/config_acceso.
            existente.tipo = datos["tipo"]
            existente.config_acceso = datos["config_acceso"]
            session.add(existente)

    session.commit()


def main() -> None:
    init_db()
    with Session(engine) as session:
        seed(session)


if __name__ == "__main__":
    main()
