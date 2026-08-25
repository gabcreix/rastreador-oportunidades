import time
from itertools import product

import httpx

from app.pipeline.ingesta.base import ItemCapturado

USER_AGENT = "RastreadorOportunidades/0.1 (uso personal; contacto: gabcreix@gmail.com)"
PAGINAS_RESENAS_POR_DEFECTO = 2


class ConectorAppleAppStore:
    """F1 · Apple App Store — descubre apps populares por top charts y lee sus
    reseñas negativas recientes (tipo "mejorar"). Dos saltos, ambos oficiales
    pero no garantizados (`07-estrategia-consultas.md` §8):

    1. Top charts (Marketing Tools RSS Feed Generator v2): no filtra por
       categoría en la ruta, así que se filtra en código por `genreId`
       (con la salvedad de que `genres` a veces viene vacío en la respuesta
       de Apple y esa app se pierde).
    2. Reseñas de esas apps (feed oficial de siempre), solo 1-2 estrellas y
       pocas páginas por app: el top charts se refresca a diario y basta con
       el pulso reciente. Corte ante 403 o página sin reseñas.
    """

    def __init__(
        self,
        paises_charts: list[str],
        tipos_chart: list[str],
        limite_chart: int,
        generos_interes: list[str],
        paises_resenas: list[str],
        paginas_resenas: int = PAGINAS_RESENAS_POR_DEFECTO,
        pausa_segundos: float = 1.0,
    ):
        self.paises_charts = paises_charts
        self.tipos_chart = tipos_chart
        self.limite_chart = limite_chart
        self.generos_interes = {str(g) for g in generos_interes}
        self.paises_resenas = paises_resenas
        self.paginas_resenas = paginas_resenas
        self.pausa_segundos = pausa_segundos

    def fetch(self) -> list[ItemCapturado]:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=10.0) as client:
            app_ids = self._descubrir_apps(client)

            items: list[ItemCapturado] = []
            for app_id in app_ids:
                for pais in self.paises_resenas:
                    items.extend(self._resenas_negativas(client, app_id, pais))
            return items

    def _descubrir_apps(self, client: httpx.Client) -> list[str]:
        app_ids: dict[str, None] = {}  # dict conserva el orden y actúa de set
        for pais, tipo in product(self.paises_charts, self.tipos_chart):
            url = f"https://rss.marketingtools.apple.com/api/v2/{pais}/apps/{tipo}/{self.limite_chart}/apps.json"
            respuesta = client.get(url)
            time.sleep(self.pausa_segundos)
            if respuesta.status_code >= 400:
                continue

            for app in respuesta.json().get("feed", {}).get("results", []):
                generos = {g.get("genreId") for g in app.get("genres", []) if g.get("genreId")}
                if generos & self.generos_interes:
                    app_ids[app["id"]] = None

        return list(app_ids)

    def _resenas_negativas(self, client: httpx.Client, app_id: str, pais: str) -> list[ItemCapturado]:
        items: list[ItemCapturado] = []
        for pagina in range(1, self.paginas_resenas + 1):
            url = (
                f"https://itunes.apple.com/{pais}/rss/customerreviews/"
                f"page={pagina}/sortBy=mostRecent/id={app_id}/json"
            )
            respuesta = client.get(url)
            time.sleep(self.pausa_segundos)

            if respuesta.status_code >= 400:
                break

            entradas = respuesta.json().get("feed", {}).get("entry", [])
            # La primera entrada de la primera página es metadata de la app, no una reseña.
            resenas = [entrada for entrada in entradas if "im:rating" in entrada]
            if not resenas:
                break

            for resena in resenas:
                puntuacion = resena.get("im:rating", {}).get("label", "")
                if puntuacion not in ("1", "2"):
                    continue
                review_id = resena.get("id", {}).get("label", "")
                titulo = resena.get("title", {}).get("label", "")
                contenido = resena.get("content", {}).get("label", "")
                texto = f"[{puntuacion}★] {titulo}\n\n{contenido}".strip()
                url_original = review_id or f"appstore:{app_id}:{pais}:{pagina}:{titulo}"
                items.append(ItemCapturado(url_original=url_original, contenido_bruto=texto))

        return items
