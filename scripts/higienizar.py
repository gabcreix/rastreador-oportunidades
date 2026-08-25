"""Aplica el filtro de higiene (Etapa 1, sin IA) a las Capturas pendientes.

Uso: python -m scripts.higienizar
"""

from sqlmodel import Session

from app.db import engine, init_db
from app.pipeline.higiene import procesar_capturas_pendientes


def main() -> None:
    init_db()
    with Session(engine) as session:
        contadores = procesar_capturas_pendientes(session)
        print(f"Procesadas: {contadores['procesada']}, descartadas: {contadores['descartada']}")


if __name__ == "__main__":
    main()
