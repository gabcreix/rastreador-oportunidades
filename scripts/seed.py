"""Crea el Perfil único inicial, sus Áreas y las 7 Fuentes de arranque del MVP.

Idempotente: se puede ejecutar varias veces sin duplicar filas.
Uso: python -m scripts.seed
"""

import json

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Area, Fuente, Perfil

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
FUENTES = [
    {
        "nombre": "Reddit — ideas",
        "tipo": "foro",
        "config_acceso": json.dumps(
            {"urls": ["https://www.reddit.com/r/SomebodyMakeThis+AppIdeas+Lightbulb/new.rss"]}
        ),
    },
    {
        "nombre": "Reddit — negocio/SaaS",
        "tipo": "foro",
        "config_acceso": json.dumps(
            {"urls": ["https://www.reddit.com/r/SaaS+Entrepreneur+smallbusiness/new.rss"]}
        ),
    },
    {
        "nombre": "Hacker News — Ask + Show",
        "tipo": "foro",
        "config_acceso": json.dumps({"urls": ["https://hnrss.org/ask", "https://hnrss.org/show"]}),
    },
    {
        "nombre": "Apple App Store — reseñas",
        "tipo": "reseñas",
        "config_acceso": json.dumps({"urls": [], "app_ids": [], "paises": ["es"]}),
    },
    {
        "nombre": "Google News — búsquedas temáticas",
        "tipo": "búsquedas",
        "config_acceso": json.dumps({"consultas": []}),
    },
    {
        "nombre": "Prensa tech (TechCrunch + Xataka)",
        "tipo": "prensa",
        "config_acceso": json.dumps(
            {"urls": ["https://techcrunch.com/feed/", "https://www.xataka.com/index.xml"]}
        ),
    },
    {
        "nombre": "Product Hunt",
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

    session.commit()


def main() -> None:
    init_db()
    with Session(engine) as session:
        seed(session)


if __name__ == "__main__":
    main()
