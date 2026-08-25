from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlmodel import Session, select

from app.models import Captura, EstadoProcesamiento, Fuente


@dataclass
class ItemCapturado:
    """Un ítem crudo devuelto por un conector, antes de convertirse en Captura."""

    url_original: str
    contenido_bruto: str


class Conector(Protocol):
    def fetch(self) -> list[ItemCapturado]: ...


def guardar_capturas(session: Session, fuente: Fuente, items: list[ItemCapturado]) -> int:
    """Persiste los items como Capturas nuevas, deduplicando por url_original.

    Nunca borra ni sobrescribe una Captura existente. Devuelve cuántas se han creado.
    """
    urls_existentes = set(
        session.exec(select(Captura.url_original).where(Captura.fuente_id == fuente.id)).all()
    )

    nuevas = 0
    for item in items:
        if item.url_original in urls_existentes:
            continue
        session.add(
            Captura(
                fuente_id=fuente.id,
                contenido_bruto=item.contenido_bruto,
                url_original=item.url_original,
                estado_procesamiento=EstadoProcesamiento.PENDIENTE,
            )
        )
        urls_existentes.add(item.url_original)
        nuevas += 1

    fuente.fecha_ultimo_rastreo = datetime.utcnow()
    session.add(fuente)
    session.commit()
    return nuevas
