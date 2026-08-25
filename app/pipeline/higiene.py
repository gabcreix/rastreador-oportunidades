import hashlib
import re

from langdetect import DetectorFactory, LangDetectException, detect
from sqlmodel import Session, select

from app.models import Captura, EstadoProcesamiento

# Resultados reproducibles entre ejecuciones (langdetect es no determinista por defecto).
DetectorFactory.seed = 0

LONGITUD_MINIMA = 15
IDIOMAS_PERMITIDOS = {"es", "en"}

# Lista corta y ampliable: solo lo obviamente spam (alto recall, no jueces de
# frontera). Ampliar aquí si se detectan patrones nuevos con el uso.
FRASES_SPAM = [
    "click here to claim",
    "you've won",
    "you have won",
    "casino bonus",
    "make money fast",
    "work from home guaranteed",
    "free airdrop",
    "crypto giveaway",
    "viagra",
]

# El mismo carácter repetido 10+ veces seguidas ("¡¡¡¡¡¡¡¡¡¡¡", "aaaaaaaaaa").
_REPETICION_SOSPECHOSA = re.compile(r"(.)\1{9,}")


def es_contenido_vacio_o_roto(contenido: str) -> bool:
    return len(contenido.strip()) < LONGITUD_MINIMA


def es_spam_evidente(contenido: str) -> bool:
    texto = contenido.lower()
    if any(frase in texto for frase in FRASES_SPAM):
        return True
    return bool(_REPETICION_SOSPECHOSA.search(contenido))


def es_idioma_fuera_de_alcance(contenido: str) -> bool:
    """Alto recall: si no se puede determinar el idioma, se deja pasar."""
    try:
        idioma = detect(contenido)
    except LangDetectException:
        return False
    return idioma not in IDIOMAS_PERMITIDOS


def hash_contenido(contenido: str) -> str:
    normalizado = " ".join(contenido.split()).lower()
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()


def procesar_capturas_pendientes(session: Session) -> dict[str, int]:
    """Etapa 1 del motor de detección (F2): filtro solo higiene.

    Nunca juzga si hay oportunidad — eso es trabajo exclusivo de la Etapa 2
    (IA, Fase 5). Marca cada Captura pendiente como `procesada` (pasa a la
    Etapa 2) o `descartada` (duplicado exacto, vacía/rota, spam evidente o
    idioma fuera de alcance). No borra nada, para poder auditar.
    """
    contadores = {"procesada": 0, "descartada": 0}

    hashes_vistos = {
        hash_contenido(contenido)
        for contenido in session.exec(
            select(Captura.contenido_bruto).where(
                Captura.estado_procesamiento != EstadoProcesamiento.PENDIENTE
            )
        ).all()
    }

    pendientes = session.exec(
        select(Captura)
        .where(Captura.estado_procesamiento == EstadoProcesamiento.PENDIENTE)
        .order_by(Captura.fecha_captura)
    ).all()

    for captura in pendientes:
        hash_actual = hash_contenido(captura.contenido_bruto)

        if (
            hash_actual in hashes_vistos
            or es_contenido_vacio_o_roto(captura.contenido_bruto)
            or es_spam_evidente(captura.contenido_bruto)
            or es_idioma_fuera_de_alcance(captura.contenido_bruto)
        ):
            captura.estado_procesamiento = EstadoProcesamiento.DESCARTADA
        else:
            captura.estado_procesamiento = EstadoProcesamiento.PROCESADA

        hashes_vistos.add(hash_actual)
        contadores[captura.estado_procesamiento.value] += 1
        session.add(captura)

    session.commit()
    return contadores
