from urllib.parse import quote

from app.pipeline.ingesta.rss import ConectorRSS


class ConectorGoogleNews(ConectorRSS):
    """F1 · Google News — feeds de búsqueda temáticos. Motor de la capa inferida (F2).

    Riesgo conocido (`06-fuentes-investigacion.md` §6): feed no documentado
    oficialmente por Google, puede cambiar de formato sin aviso.
    """

    def __init__(self, consultas: list[str], idioma: str = "es-ES", pais: str = "ES"):
        idioma_corto = idioma.split("-")[0]
        urls = [
            f"https://news.google.com/rss/search?q={quote(consulta)}&hl={idioma}&gl={pais}&ceid={pais}:{idioma_corto}"
            for consulta in consultas
        ]
        super().__init__(urls)
