import time
from urllib.parse import quote_plus

import feedparser

from app.pipeline.ingesta.articulo import resolver_y_extraer
from app.pipeline.ingesta.base import ItemCapturado
from app.pipeline.ingesta.rss import ConectorRSS

# hl -> (gl, ceid). Ver `07-estrategia-consultas.md` §1.1: una misma consulta
# en es-ES y en en-US devuelve conjuntos distintos, así que los temas
# bilingües lanzan las dos variantes con la misma q.
_LOCALES = {
    "es-ES": ("ES", "ES:es"),
    "en-US": ("US", "US:en"),
}

MAX_CARACTERES_ARTICULO = 8000


class ConectorGoogleNews(ConectorRSS):
    """F1 · Google News — catálogo de consultas de búsqueda (`07-estrategia-consultas.md`).

    Motor de la capa inferida (F2). El `summary` del feed es mínimo y el
    `link` es una redirección de Google: para darle a la IA algo más que un
    titular, se resuelve la redirección y se extrae el texto del artículo
    (`articulo.py`). Si no se puede, cae al `summary` de siempre — nunca
    bloquea el rastreo. Riesgo conocido: feed no documentado oficialmente
    por Google, puede cambiar de formato sin aviso.
    """

    def __init__(self, consultas: list[dict], pausa_segundos: float = 0.5):
        urls = []
        for consulta in consultas:
            for idioma in consulta.get("idiomas", ["es-ES"]):
                gl, ceid = _LOCALES[idioma]
                urls.append(
                    f"https://news.google.com/rss/search?q={quote_plus(consulta['q'])}"
                    f"&hl={idioma}&gl={gl}&ceid={ceid}"
                )
        super().__init__(urls)
        self.pausa_segundos = pausa_segundos

    def fetch(self) -> list[ItemCapturado]:
        items: list[ItemCapturado] = []
        for url in self.urls:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                enlace = entry.get("link", "")
                titulo = entry.get("title", "")
                resumen = entry.get("summary", "") or entry.get("description", "")
                if not enlace or not (titulo or resumen):
                    continue

                texto_articulo = resolver_y_extraer(enlace)
                time.sleep(self.pausa_segundos)
                cuerpo = texto_articulo[:MAX_CARACTERES_ARTICULO] if texto_articulo else resumen

                contenido = f"{titulo}\n\n{cuerpo}".strip()
                if not contenido:
                    continue
                items.append(ItemCapturado(url_original=enlace, contenido_bruto=contenido))
        return items
