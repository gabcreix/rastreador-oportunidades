"""Inspecciona el contenido_bruto de una muestra de Capturas de una Fuente.
Útil para depurar si un conector está trayendo texto suficiente (p. ej. si
Google News está extrayendo el artículo completo o cayendo al resumen).

Uso: python -m scripts.inspeccionar "<nombre de la fuente>" [n_capturas]
"""

import sys

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Captura, Fuente


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit('Uso: python -m scripts.inspeccionar "<nombre de la fuente>" [n_capturas]')

    nombre_fuente = sys.argv[1]
    limite = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    init_db()
    with Session(engine) as session:
        capturas = session.exec(
            select(Captura).join(Fuente).where(Fuente.nombre == nombre_fuente).limit(limite)
        ).all()

        if not capturas:
            print(f"No hay Capturas de la fuente {nombre_fuente!r}.")
            return

        for captura in capturas:
            print(f"\n=== Captura #{captura.id} — {len(captura.contenido_bruto)} caracteres ===")
            print(f"  {captura.url_original}")
            print(f"  {captura.contenido_bruto[:500]}")


if __name__ == "__main__":
    main()
