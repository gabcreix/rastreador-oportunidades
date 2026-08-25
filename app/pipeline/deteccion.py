from dataclasses import dataclass
from typing import Protocol

import anthropic

from app.config import settings
from app.models import CapaDeteccion, Captura, TipoOportunidad


@dataclass
class OportunidadCandidata:
    """Salida de la Etapa 2 (F2), antes de puntuar (F3). Aún no es una fila
    de Oportunidad: solo se persiste si supera el umbral de la Fase 6.
    """

    titulo: str
    descripcion: str
    tipo: TipoOportunidad
    capa: CapaDeteccion
    justificacion: str


class DetectorIA(Protocol):
    def detectar(self, captura: Captura) -> list[OportunidadCandidata]: ...


NOMBRE_HERRAMIENTA = "reportar_oportunidades"

_HERRAMIENTA_REPORTAR = {
    "name": NOMBRE_HERRAMIENTA,
    "description": (
        "Reporta las oportunidades de negocio/desarrollo detectadas en el texto, si las hay. "
        "Si no hay ninguna, reporta una lista vacía."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "oportunidades": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "titulo": {"type": "string", "description": "La oportunidad en una frase."},
                        "descripcion": {
                            "type": "string",
                            "description": "Qué necesidad o dolor concreto resuelve.",
                        },
                        "tipo": {"type": "string", "enum": [t.value for t in TipoOportunidad]},
                        "capa": {"type": "string", "enum": [c.value for c in CapaDeteccion]},
                        "justificacion": {
                            "type": "string",
                            "description": "Por qué esto es una oportunidad real y no solo ruido.",
                        },
                    },
                    "required": ["titulo", "descripcion", "tipo", "capa", "justificacion"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["oportunidades"],
        "additionalProperties": False,
    },
    "strict": True,
}

# Borrador v1 — a validar y ajustar con Gabriel (Fase 5 del plan de
# implementación). Basado en la definición de oportunidad y los dos niveles
# de detección de `01-descubrimiento.md`.
SYSTEM_PROMPT = """\
Eres el motor de detección de oportunidades de un rastreador personal. Lees un \
fragmento de texto (un post de Reddit, un hilo de Hacker News, una reseña de \
app, un titular y resumen de prensa...) y decides si contiene una o más \
OPORTUNIDADES.

Definición de oportunidad: una señal, detectable en el texto, de una \
necesidad real e insuficientemente cubierta, sobre la que alguien podría \
actuar con una ventaja razonable (construyendo, mejorando o invirtiendo). No \
es simple novedad ni una opinión sin sustancia.

Tipos:
- "mejorar": algo que existe pero funciona mal, es caro, lento o \
insatisfactorio (p. ej. una reseña negativa concreta, una queja repetida).
- "hueco": algo que no existe y hace falta (p. ej. "ojalá existiera una app \
que...", una necesidad sin oferta visible).
- "inversion": una ocasión de inversión o iniciativa rentable. Tipo \
secundario: úsalo con más cautela que los otros dos.

Dos capas de detección:
- "explicita": la oportunidad YA está formulada casi literalmente en el \
texto (alguien pide algo, se queja de algo concreto, pregunta si existe una \
herramienta). Aquí recopilas, interpretas poco.
- "inferida": nadie ha formulado la oportunidad; la deduces leyendo entre \
líneas. Ejemplo: una noticia dice "los jóvenes no encuentran empleo junior" \
→ deduces la oportunidad "un buscador de empleo especializado en primeros \
empleos". Aquí razonas y sintetizas, no citas.

Reglas:
- Puede haber CERO oportunidades en el texto (lo normal en spam, ruido o \
contenido irrelevante): reporta una lista vacía, no inventes para rellenar.
- Puede haber varias oportunidades distintas en el mismo texto (sobre todo \
en artículos de prensa densos): repórtalas todas por separado.
- La "justificación" explica en 1-2 frases por qué es una oportunidad real y \
no solo ruido; en la capa inferida, explica también el razonamiento que \
conecta el texto con la oportunidad deducida.
- No te corresponde puntuar la oportunidad ni juzgar si encaja con el \
perfil de nadie: eso es un paso posterior. Solo detecta y describe.
- Ante la duda sobre si algo es una oportunidad real, prioriza no \
reportarla antes que inventar una para rellenar.
"""


class DetectorAnthropic:
    """Implementación de referencia de DetectorIA con la API de Anthropic."""

    def __init__(self, client: anthropic.Anthropic | None = None, model: str | None = None):
        self.client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = model or settings.anthropic_model

    def detectar(self, captura: Captura) -> list[OportunidadCandidata]:
        mensaje_usuario = (
            f"Fuente: {captura.fuente.nombre} ({captura.fuente.tipo})\n\nTexto:\n{captura.contenido_bruto}"
        )

        respuesta = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            tools=[_HERRAMIENTA_REPORTAR],
            tool_choice={"type": "tool", "name": NOMBRE_HERRAMIENTA},
            messages=[{"role": "user", "content": mensaje_usuario}],
        )

        bloque = next((b for b in respuesta.content if b.type == "tool_use"), None)
        if bloque is None:
            return []

        return [
            OportunidadCandidata(
                titulo=item["titulo"],
                descripcion=item["descripcion"],
                tipo=TipoOportunidad(item["tipo"]),
                capa=CapaDeteccion(item["capa"]),
                justificacion=item["justificacion"],
            )
            for item in bloque.input.get("oportunidades", [])
        ]
