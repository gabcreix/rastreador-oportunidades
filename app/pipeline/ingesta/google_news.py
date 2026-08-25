from urllib.parse import quote_plus

from app.pipeline.ingesta.rss import ConectorRSS

# hl -> (gl, ceid). Ver `07-estrategia-consultas.md` §1.1: una misma consulta
# en es-ES y en en-US devuelve conjuntos distintos, así que los temas
# bilingües lanzan las dos variantes con la misma q.
_LOCALES = {
    "es-ES": ("ES", "ES:es"),
    "en-US": ("US", "US:en"),
}


class ConectorGoogleNews(ConectorRSS):
    """F1 · Google News — catálogo de consultas de búsqueda (`07-estrategia-consultas.md`).

    Motor de la capa inferida (F2). Riesgo conocido: feed no documentado
    oficialmente por Google, puede cambiar de formato sin aviso.
    """

    def __init__(self, consultas: list[dict]):
        urls = []
        for consulta in consultas:
            for idioma in consulta.get("idiomas", ["es-ES"]):
                gl, ceid = _LOCALES[idioma]
                urls.append(
                    f"https://news.google.com/rss/search?q={quote_plus(consulta['q'])}"
                    f"&hl={idioma}&gl={gl}&ceid={ceid}"
                )
        super().__init__(urls)
