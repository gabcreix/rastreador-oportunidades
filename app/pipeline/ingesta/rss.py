import feedparser

from app.pipeline.ingesta.base import ItemCapturado


class ConectorRSS:
    """Conector genérico para fuentes RSS/Atom estándar (una o varias URLs).

    Cubre Hacker News (hnrss.org), Product Hunt y la prensa tech (TechCrunch,
    Xataka) tal cual; Google News lo reutiliza componiendo primero las URLs
    de búsqueda (ver `google_news.py`).
    """

    def __init__(self, urls: list[str]):
        self.urls = urls

    def fetch(self) -> list[ItemCapturado]:
        items: list[ItemCapturado] = []
        for url in self.urls:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                enlace = entry.get("link", "")
                titulo = entry.get("title", "")
                resumen = entry.get("summary", "") or entry.get("description", "")
                contenido = f"{titulo}\n\n{resumen}".strip()
                if not enlace or not contenido:
                    continue
                items.append(ItemCapturado(url_original=enlace, contenido_bruto=contenido))
        return items
