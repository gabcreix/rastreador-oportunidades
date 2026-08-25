"""Ejecuta el conector de una Fuente concreta contra la red real y guarda las
Capturas nuevas en SQLite. Útil para probar un conector de forma aislada,
antes de que exista el orquestador completo del pipeline (Fase 8).

Uso: python -m scripts.rastrear "Hacker News — Ask + Show"
"""

import sys

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Fuente
from app.pipeline.ingesta.base import guardar_capturas
from app.pipeline.ingesta.factory import crear_conector


def rastrear(nombre_fuente: str) -> int:
    init_db()
    with Session(engine) as session:
        fuente = session.exec(select(Fuente).where(Fuente.nombre == nombre_fuente)).first()
        if fuente is None:
            raise SystemExit(
                f"No existe ninguna Fuente llamada {nombre_fuente!r}. "
                "Ejecuta antes `python -m scripts.seed`."
            )

        conector = crear_conector(fuente)
        items = conector.fetch()
        nuevas = guardar_capturas(session, fuente, items)
        print(f"{fuente.nombre}: {len(items)} items recibidos, {nuevas} Capturas nuevas guardadas.")
        return nuevas


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit('Uso: python -m scripts.rastrear "<nombre de la fuente>"')
    rastrear(sys.argv[1])
