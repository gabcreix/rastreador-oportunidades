import html
import re
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
_TAG_HTML = re.compile(r"<[^>]+>")


def _limpiar_html(texto: str) -> str:
    """El `summary` de Google News trae HTML crudo (un enlace + la fuente en
    <font>), no texto plano. Se usa solo como último recurso, si no se pudo
    extraer el artículo."""
    return html.unescape(_TAG_HTML.sub(" ", texto)).strip()


class ConectorGoogleNews(ConectorRSS):
    """F1 · Google News — catálogo de consultas de búsqueda (`07-estrategia-consultas.md`).

    Motor de la capa inferida (F2). El `summary` del feed es mínimo y en HTML
    crudo, y el `link` es una redirección de Google que no resuelve con un
    simple `follow_redirects` (la resolución final la hace una llamada
    interna de Google, no un 302 HTTP): se decodifica y se extrae el texto
    del artículo (`articulo.py`). Si no se puede, cae al `summary` limpio de
    HTML — nunca bloquea el rastreo. Riesgo conocido: feed no documentado
    oficialmente por Google, puede cambiar de formato sin aviso.
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

                url_final, texto_articulo = resolver_y_extraer(enlace)
                time.sleep(self.pausa_segundos)
                cuerpo = texto_articulo[:MAX_CARACTERES_ARTICULO] if texto_articulo else _limpiar_html(resumen)

                contenido = f"{titulo}\n\n{cuerpo}".strip()
                if not contenido:
                    continue
                items.append(ItemCapturado(url_original=url_final, contenido_bruto=contenido))
        return items
