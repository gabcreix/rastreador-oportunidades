"""Migración puntual: añade a Oportunidad las columnas del schema de valor
(v3 del motor de detección — solucion_propuesta, evidencia_demanda,
solucion_existente) si la tabla ya existía sin ellas. Idempotente: no falla
si ya están.

Uso: python -m scripts.migrar
"""

from sqlalchemy import inspect, text

from app.db import engine, init_db

COLUMNAS_NUEVAS = {
    "solucion_propuesta": "TEXT NOT NULL DEFAULT ''",
    "evidencia_demanda": "TEXT NOT NULL DEFAULT ''",
    "solucion_existente": "TEXT NOT NULL DEFAULT ''",
}


def main() -> None:
    init_db()
    inspector = inspect(engine)

    if "oportunidad" not in inspector.get_table_names():
        print("La tabla 'oportunidad' no existe todavía; nada que migrar.")
        return

    columnas_actuales = {columna["name"] for columna in inspector.get_columns("oportunidad")}

    with engine.begin() as conexion:
        for nombre, definicion in COLUMNAS_NUEVAS.items():
            if nombre in columnas_actuales:
                continue
            conexion.execute(text(f"ALTER TABLE oportunidad ADD COLUMN {nombre} {definicion}"))
            print(f"Añadida columna: {nombre}")

    print("Migración completada (o ya estaba al día).")


if __name__ == "__main__":
    main()
