import time

import httpx

from app.pipeline.ingesta.base import ItemCapturado

USER_AGENT = "RastreadorOportunidades/0.1 (uso personal; contacto: gabcreix@gmail.com)"
MAX_PAGINAS = 10


class ConectorAppleAppStore:
    """F1 · Apple App Store — reseñas de clientes (RSS/JSON oficial). Explícita, tipo "mejorar".

    Riesgos conocidos (`06-fuentes-investigacion.md` §6): tope de ~500 reseñas
    por app/país y 403 temporales si se abusa. Ritmo bajo por defecto
    (`pausa_segundos`) y corte inmediato ante un 403 o una página sin reseñas.
    """

    def __init__(self, app_ids: list[str], paises: list[str], pausa_segundos: float = 1.0):
        self.app_ids = app_ids
        self.paises = paises
        self.pausa_segundos = pausa_segundos

    def fetch(self) -> list[ItemCapturado]:
        items: list[ItemCapturado] = []
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=10.0) as client:
            for app_id in self.app_ids:
                for pais in self.paises:
                    items.extend(self._fetch_app_pais(client, app_id, pais))
        return items

    def _fetch_app_pais(self, client: httpx.Client, app_id: str, pais: str) -> list[ItemCapturado]:
        items: list[ItemCapturado] = []
        for pagina in range(1, MAX_PAGINAS + 1):
            url = (
                f"https://itunes.apple.com/{pais}/rss/customerreviews/"
                f"page={pagina}/sortBy=mostRecent/id={app_id}/json"
            )
            respuesta = client.get(url)
            time.sleep(self.pausa_segundos)

            if respuesta.status_code == 403:
                break
            respuesta.raise_for_status()

            entradas = respuesta.json().get("feed", {}).get("entry", [])
            # La primera entrada de la primera página es metadata de la app, no una reseña.
            resenas = [entrada for entrada in entradas if "im:rating" in entrada]
            if not resenas:
                break

            for resena in resenas:
                review_id = resena.get("id", {}).get("label", "")
                titulo = resena.get("title", {}).get("label", "")
                contenido = resena.get("content", {}).get("label", "")
                puntuacion = resena.get("im:rating", {}).get("label", "")
                texto = f"[{puntuacion}★] {titulo}\n\n{contenido}".strip()
                url_original = review_id or f"appstore:{app_id}:{pais}:{pagina}:{titulo}"
                items.append(ItemCapturado(url_original=url_original, contenido_bruto=texto))

        return items
