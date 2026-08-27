import logging
from dataclasses import dataclass
from typing import Protocol

import anthropic

from app.config import settings
from app.models import CapaDeteccion, Captura, TipoOportunidad

logger = logging.getLogger(__name__)


@dataclass
class OportunidadCandidata:
    """Salida de la Etapa 2 (F2), antes de puntuar (F3). Aún no es una fila
    de Oportunidad: solo se persiste si supera el umbral de la Fase 6.
    """

    titulo: str
    descripcion: str  # la necesidad/dolor subyacente, sin solución
    solucion_propuesta: str
    tipo: TipoOportunidad
    capa: CapaDeteccion
    evidencia_demanda: str
    solucion_existente: str
    justificacion: str


class DetectorIA(Protocol):
    def detectar(self, captura: Captura) -> list[OportunidadCandidata]: ...


NOMBRE_HERRAMIENTA = "reportar_oportunidades"

_HERRAMIENTA_REPORTAR = {
    "name": NOMBRE_HERRAMIENTA,
    "description": (
        "Reporta las oportunidades detectadas, si las hay, tras razonar en "
        "'analisis_previo'. Si no hay ninguna, 'oportunidades' es una lista vacía."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "analisis_previo": {
                "type": "string",
                "description": (
                    "Razonamiento del checklist ANTES de decidir. No se guarda. "
                    "Aplica los 4 puntos y concluye qué reportar (o nada)."
                ),
            },
            "oportunidades": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "titulo": {"type": "string", "description": "La oportunidad en una frase."},
                        "descripcion": {
                            "type": "string",
                            "description": (
                                "La necesidad/dolor subyacente, sin solución; quién lo sufre y "
                                "el disparador."
                            ),
                        },
                        "solucion_propuesta": {
                            "type": "string",
                            "description": "Qué se construiría o mejoraría. Vacío si es necesidad pura.",
                        },
                        "tipo": {"type": "string", "enum": [t.value for t in TipoOportunidad]},
                        "capa": {"type": "string", "enum": [c.value for c in CapaDeteccion]},
                        "evidencia_demanda": {
                            "type": "string",
                            "description": "Qué señala demanda real en el texto y cuán fuerte.",
                        },
                        "solucion_existente": {
                            "type": "string",
                            "description": "Solución directa ya existente, o cadena vacía.",
                        },
                        "justificacion": {
                            "type": "string",
                            "description": "Por qué es real y no ruido; razonamiento en inferida.",
                        },
                    },
                    "required": [
                        "titulo",
                        "descripcion",
                        "solucion_propuesta",
                        "tipo",
                        "capa",
                        "evidencia_demanda",
                        "solucion_existente",
                        "justificacion",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["analisis_previo", "oportunidades"],
        "additionalProperties": False,
    },
    "strict": True,
}

# v3 — ajustado tras dos rondas de prueba real (ver historial de decisiones).
# Añade few-shot, razonamiento previo (analisis_previo), schema de valor
# (necesidad/solución/demanda/solución existente) y lente de señal por tipo
# de fuente.
SYSTEM_PROMPT = """\
Eres el motor de detección de oportunidades de un rastreador personal. Lees un \
fragmento de texto (un post de Reddit, un hilo de Hacker News, una reseña de \
app, un artículo de prensa...) y decides si contiene una o más OPORTUNIDADES, \
extrayendo el máximo valor de cada una.

Definición de oportunidad: una señal, detectable en el texto, de una necesidad \
real e insuficientemente cubierta, sobre la que alguien podría actuar con una \
ventaja razonable (construyendo, mejorando o invirtiendo). No es simple novedad \
ni una opinión sin sustancia.

Tipos:
- "mejorar": algo que existe pero funciona mal, es caro, lento o insatisfactorio.
- "hueco": algo que no existe y hace falta (una necesidad sin oferta visible).
- "inversion": una ocasión de inversión o iniciativa rentable. Secundario: úsalo \
con más cautela.

Capas:
- "explicita": la oportunidad ya está formulada casi literalmente (alguien pide, \
se queja o pregunta si existe algo). Recopilas, interpretas poco.
- "inferida": nadie la ha formulado; la deduces leyendo entre líneas. Razonas y \
sintetizas. En inferida debes nombrar un segmento/producto CONCRETO Y ESTRECHO; \
rechaza salidas vagas tipo "categoría de mercado", "modernización de X" o \
"consultoría para Y".

Naturaleza de la fuente (úsala como lente):
- Texto que empieza por "Show HN:" o proveniente de Product Hunt = un producto YA \
LANZADO. No es un "hueco" (alguien ya lo construyó); solo repórtalo si hay un \
ángulo de mejora concreto y distinto sobre lo lanzado (tipo "mejorar"), y dilo.
- "Ask HN:" o subreddits de ideas = una necesidad expresada (buen terreno de hueco).
- Reseña de app (Apple) = insatisfacción con algo existente (terreno de "mejorar").
- Noticia/prensa = materia prima de la capa inferida.

Para CADA oportunidad, rellena:
- titulo: la oportunidad en una frase.
- descripcion: la NECESIDAD o dolor subyacente, SIN solución. Di quién lo sufre y \
cuál es el disparador.
- solucion_propuesta: qué se construiría o mejoraría. Puede quedar vacío si es una \
necesidad pura sin solución obvia.
- tipo, capa.
- evidencia_demanda: qué en el texto indica demanda real y cuán fuerte (cuánta \
gente, intensidad del dolor, si es patrón repetido o un caso aislado).
- solucion_existente: si ya existe algo directo que lo cubre, nómbralo; "" si no se \
conoce ninguno.
- justificacion: por qué es una oportunidad real y no ruido (1-2 frases). En \
inferida, explica el razonamiento que conecta el texto con la oportunidad deducida.

Reglas de calidad — PRECISIÓN SOBRE COBERTURA. En la gran mayoría de textos NO hay \
oportunidad; reportar es la excepción. Primero escribe tu razonamiento en \
"analisis_previo" aplicando este checklist, y solo después decide qué va en \
"oportunidades":
1. ¿Ya existe una solución ampliamente conocida (aunque el texto no la cite)? \
Espacios saturados donde NO reportar "hueco": comparadores de suscripciones, guías \
genéricas de prompt engineering, guías de tarifas para freelancers, "mejores apps \
para X". Rellena "solucion_existente" si aplica.
2. ¿Es una necesidad de producto concreta y accionable, o solo una queja personal, \
un desahogo o una opinión? Un lamento de carrera o una queja puntual NO es por sí \
sola una oportunidad.
3. ¿Alguien con solo este texto podría describir qué construir? Si es tan vaga que \
no se puede empezar nada concreto, no la reportes.
4. ¿El texto es el anuncio de un producto que YA hace esto? Entonces no es un hueco; \
solo repórtalo si hay una mejora concreta sobre lo lanzado.

No reportes la misma necesidad dos veces como "hueco" y como "mejorar": elige el \
encuadre dominante. Ante dudas razonables en cualquier punto, no reportes.

No puntúas ni juzgas el encaje con ningún perfil: eso es un paso posterior. Solo \
detecta, describe y extrae valor.

EJEMPLOS

[Ejemplo 1 — explícita buena, Ask HN]
Texto: "Ask HN: Busco una pantalla e-ink grande (>20\\") y táctil para un calendario \
de pared. Solo encuentro pequeñas o no táctiles."
analisis_previo: Petición directa; combinación (e-ink + grande + táctil) rara en el \
mercado; no es queja personal; se puede describir qué construir. Reportar.
oportunidad: titulo="Pantalla e-ink grande y táctil de bajo consumo"; \
descripcion="Quien monta paneles de información/calendarios no encuentra e-ink >20\\" \
con táctil y bajo consumo"; solucion_propuesta="Fabricar/integrar un panel e-ink \
grande con capa táctil de bajo consumo"; tipo="hueco"; capa="explicita"; \
evidencia_demanda="Búsqueda activa que no encuentra oferta; nicho recurrente en foros \
de domótica"; solucion_existente=""; justificacion="Necesidad concreta y construible \
con oferta escasa".

[Ejemplo 2 — inferida buena, prensa]
Texto: "Reportaje: los jóvenes no encuentran su primer empleo; las plataformas \
generalistas mezclan ofertas senior y junior y sus filtros no ayudan a quien no \
tiene experiencia."
analisis_previo: La noticia no formula oportunidad; se deduce un hueco concreto \
(bolsa de primer empleo). Segmento estrecho y construible. Reportar como inferida.
oportunidad: titulo="Bolsa de empleo especializada en primer empleo junior"; \
descripcion="Los recién titulados no tienen un canal donde las ofertas junior no se \
diluyan entre las senior"; solucion_propuesta="Plataforma de empleo filtrada solo a \
primer empleo, con criterios sin-experiencia"; tipo="hueco"; capa="inferida"; \
evidencia_demanda="Reportaje describe fricción de un colectivo amplio"; \
solucion_existente="Portales generalistas, pero no especializados en junior"; \
justificacion="De la fricción descrita se deduce un segmento desatendido y acotable".

[Ejemplo 3 — vacío, Show HN de espacio saturado]
Texto: "Show HN: Lancé otro comparador de suscripciones de software para no pagar de \
más."
analisis_previo: Es un producto ya lanzado (Show HN) y en un espacio saturadísimo \
(comparadores de suscripciones). Punto 1 y punto 4 fallan. No reportar.
oportunidades: [].

[Ejemplo 4 — vacío, queja personal]
Texto: "Llevo diez años programando y últimamente siento que mi trabajo ha perdido \
todo el sentido."
analisis_previo: Desahogo personal, sin necesidad de producto concreta ni patrón \
construible. Punto 2 falla. No reportar.
oportunidades: [].
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
            max_tokens=2048,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            tools=[_HERRAMIENTA_REPORTAR],
            tool_choice={"type": "tool", "name": NOMBRE_HERRAMIENTA},
            messages=[{"role": "user", "content": mensaje_usuario}],
        )

        bloque = next((b for b in respuesta.content if b.type == "tool_use"), None)
        if bloque is None:
            return []

        # Scratchpad de razonamiento: nunca se persiste, solo se loguea para depurar.
        logger.debug("analisis_previo (captura %s): %s", captura.id, bloque.input.get("analisis_previo", ""))

        return [
            OportunidadCandidata(
                titulo=item["titulo"],
                descripcion=item["descripcion"],
                solucion_propuesta=item["solucion_propuesta"],
                tipo=TipoOportunidad(item["tipo"]),
                capa=CapaDeteccion(item["capa"]),
                evidencia_demanda=item["evidencia_demanda"],
                solucion_existente=item["solucion_existente"],
                justificacion=item["justificacion"],
            )
            for item in bloque.input.get("oportunidades", [])
        ]
