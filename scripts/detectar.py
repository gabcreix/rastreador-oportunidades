"""Ejecuta el motor de detección (Etapa 2, IA) sobre una muestra de Capturas
ya procesadas por la higiene, e imprime las oportunidades candidatas
detectadas. No persiste nada todavía (eso llega con el scoring, Fase 6):
esto es para revisar la calidad del prompt antes de escalarlo a todo el
histórico.

Uso: python -m scripts.detectar [n_capturas] ["nombre de la fuente"]
     (n_capturas por defecto 20; sin fuente, coge de cualquiera)
"""

import sys

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Captura, EstadoProcesamiento, Fuente
from app.pipeline.deteccion import DetectorAnthropic


def main() -> None:
    limite = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    nombre_fuente = sys.argv[2] if len(sys.argv) > 2 else None

    init_db()
    detector = DetectorAnthropic()

    with Session(engine) as session:
        consulta = select(Captura).where(Captura.estado_procesamiento == EstadoProcesamiento.PROCESADA)
        if nombre_fuente:
            consulta = consulta.join(Fuente).where(Fuente.nombre == nombre_fuente)
        capturas = session.exec(consulta.limit(limite)).all()

        total_candidatas = 0
        for captura in capturas:
            candidatas = detector.detectar(captura)
            total_candidatas += len(candidatas)
            if not candidatas:
                continue
            print(f"\n=== Captura #{captura.id} ({captura.fuente.nombre}) ===")
            print(f"  {captura.url_original}")
            for candidata in candidatas:
                print(f"  · [{candidata.tipo.value}/{candidata.capa.value}] {candidata.titulo}")
                print(f"    Necesidad: {candidata.descripcion}")
                if candidata.solucion_propuesta:
                    print(f"    Solución propuesta: {candidata.solucion_propuesta}")
                print(f"    Evidencia de demanda: {candidata.evidencia_demanda}")
                if candidata.solucion_existente:
                    print(f"    Solución existente: {candidata.solucion_existente}")
                print(f"    Justificación: {candidata.justificacion}")

        print(f"\n{len(capturas)} Capturas analizadas, {total_candidatas} oportunidades candidatas detectadas.")


if __name__ == "__main__":
    main()
