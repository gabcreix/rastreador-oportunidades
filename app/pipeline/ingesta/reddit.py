import logging
import time
from urllib.parse import quote_plus

import feedparser
import httpx

from app.pipeline.ingesta.base import ItemCapturado
from app.pipeline.ingesta.rss import items_desde_feed

logger = logging.getLogger(__name__)

USER_AGENT = "RastreadorOportunidades/0.1 (uso personal; contacto: gabcreix@gmail.com)"


class ConectorReddit:
    """F1 · Reddit — feeds `new.rss` de subreddits + catálogo de consultas
    `search.rss` (`07-estrategia-consultas.md`).

    Riesgo conocido (`00-parking.md`): Reddit devuelve 403 a IPs de
    datacenter/VPS. Mitigación: User-Agent propio y ritmo bajo; si una URL
    de esta Fuente falla (403 u otro error), se registra y se sigue con las
    demás en vez de tumbar el resto del rastreo.
    """

    def __init__(self, urls_new: list[str], consultas: list[dict], pausa_segundos: float = 2.0):
        self.urls_new = urls_new
        self.consultas = consultas
        self.pausa_segundos = pausa_segundos

    def fetch(self) -> list[ItemCapturado]:
        items: list[ItemCapturado] = []
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=10.0) as client:
            for url in self.urls_new:
                items.extend(self._fetch_feed(client, url))
                time.sleep(self.pausa_segundos)
            for consulta in self.consultas:
                items.extend(self._fetch_feed(client, self._url_busqueda(consulta)))
                time.sleep(self.pausa_segundos)
        return items

    @staticmethod
    def _url_busqueda(consulta: dict) -> str:
        q = quote_plus(consulta["q"])
        if consulta.get("scope") == "subreddit":
            return f"https://www.reddit.com/r/{consulta['subs']}/search.rss?q={q}&restrict_sr=1&sort=new"
        return f"https://www.reddit.com/search.rss?q={q}&sort=new"

    def _fetch_feed(self, client: httpx.Client, url: str) -> list[ItemCapturado]:
        try:
            respuesta = client.get(url)
        except httpx.HTTPError as exc:
            logger.warning("Reddit: fallo de red en %s (%s)", url, exc)
            return []

        if respuesta.status_code == 403:
            logger.warning("Reddit: 403 (bloqueo por IP de datacenter) en %s", url)
            return []
        if respuesta.status_code >= 400:
            logger.warning("Reddit: HTTP %s en %s", respuesta.status_code, url)
            return []

        items = items_desde_feed(feedparser.parse(respuesta.content))
        if not items:
            logger.info("Reddit: 0 items (HTTP 200, feed vacío, no bloqueado) en %s", url)
        return items
