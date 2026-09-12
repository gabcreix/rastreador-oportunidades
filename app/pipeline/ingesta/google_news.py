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

    `url_original` guarda el enlace de redirección de Google (no la URL real
    decodificada): es estable entre rastreos de un mismo artículo y un
    navegador sí lo resuelve bien (el problema es solo con clientes HTTP
    scriptados). Guardarlo así permite saltarse `urls_conocidas` — artículos
    ya capturados en un rastreo anterior — ANTES de pagar el coste de
    decodificar y descargar, que es lo que hace lento un re-rastreo.
    """

    def __init__(
        self,
        consultas: list[dict],
        pausa_segundos: float = 0.5,
        urls_conocidas: set[str] | None = None,
    ):
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
        self.urls_conocidas = set(urls_conocidas) if urls_conocidas else set()

    def fetch(self) -> list[ItemCapturado]:
        items: list[ItemCapturado] = []
        for url in self.urls:
            entradas = feedparser.parse(url).entries
            for indice, entry in enumerate(entradas, start=1):
                enlace = entry.get("link", "")
                titulo = entry.get("title", "")
                resumen = entry.get("summary", "") or entry.get("description", "")
                if not enlace or not (titulo or resumen):
                    continue

                if enlace in self.urls_conocidas:
                    continue

                print(f"  Google News [{indice}/{len(entradas)}]: extrayendo — {titulo[:70]}")
                _, texto_articulo = resolver_y_extraer(enlace)
                time.sleep(self.pausa_segundos)
                cuerpo = texto_articulo[:MAX_CARACTERES_ARTICULO] if texto_articulo else _limpiar_html(resumen)

                contenido = f"{titulo}\n\n{cuerpo}".strip()
                if not contenido:
                    continue
                items.append(ItemCapturado(url_original=enlace, contenido_bruto=contenido))
                self.urls_conocidas.add(enlace)  # evita reprocesar si sale en más de una consulta
        return items
