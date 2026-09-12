from app.pipeline.ingesta.google_news import ConectorGoogleNews
from app.pipeline.ingesta.rss import ConectorRSS

FEED_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Test Feed</title>
<item>
  <title>Alguien pide una app para X</title>
  <link>https://example.com/post/1</link>
  <description>Ojalá existiera una app que hiciera X</description>
</item>
<item>
  <title>Sin descripcion</title>
  <link>https://example.com/post/2</link>
</item>
<item>
  <title>Sin enlace</title>
  <description>Este item no tiene link y debe descartarse</description>
</item>
</channel></rss>
"""


def test_conector_rss_extrae_titulo_y_resumen():
    conector = ConectorRSS(urls=[FEED_XML])

    items = conector.fetch()

    assert len(items) == 2
    assert items[0].url_original == "https://example.com/post/1"
    assert "Ojalá existiera una app que hiciera X" in items[0].contenido_bruto
    assert items[1].url_original == "https://example.com/post/2"


def test_conector_google_news_consulta_bilingue_lanza_dos_locales():
    conector = ConectorGoogleNews(
        consultas=[{"id": "I-GN-A1", "q": '"data engineering"', "idiomas": ["es-ES", "en-US"]}]
    )

    assert len(conector.urls) == 2
    assert any("hl=es-ES" in u and "gl=ES" in u and "ceid=ES:es" in u for u in conector.urls)
    assert any("hl=en-US" in u and "gl=US" in u and "ceid=US:en" in u for u in conector.urls)


def test_conector_google_news_consulta_de_un_solo_idioma():
    conector = ConectorGoogleNews(
        consultas=[{"id": "E-GN-01", "q": '"no existe una app"', "idiomas": ["es-ES"]}]
    )

    assert len(conector.urls) == 1
    assert "hl=es-ES" in conector.urls[0]


def test_conector_google_news_sustituye_el_resumen_por_el_articulo_completo(monkeypatch):
    monkeypatch.setattr(
        "app.pipeline.ingesta.google_news.resolver_y_extraer",
        lambda url: (url, "Texto completo del artículo, con mucho más detalle que el resumen."),
    )
    conector = ConectorGoogleNews(consultas=[{"q": "x", "idiomas": ["es-ES"]}], pausa_segundos=0)
    conector.urls = [FEED_XML]

    items = conector.fetch()

    assert len(items) == 2
    assert "Texto completo del artículo" in items[0].contenido_bruto
    assert "Ojalá existiera una app que hiciera X" not in items[0].contenido_bruto


def test_conector_google_news_url_original_es_el_enlace_del_feed_no_el_decodificado(monkeypatch):
    # url_original se queda con el enlace de Google (estable entre rastreos,
    # y un navegador sí lo resuelve): la URL decodificada solo se usa para
    # poder descargar y extraer el artículo, no se persiste.
    monkeypatch.setattr(
        "app.pipeline.ingesta.google_news.resolver_y_extraer",
        lambda url: ("https://medio.example/real", "Texto del artículo."),
    )
    conector = ConectorGoogleNews(consultas=[{"q": "x", "idiomas": ["es-ES"]}], pausa_segundos=0)
    conector.urls = [FEED_XML]

    items = conector.fetch()

    assert items[0].url_original == "https://example.com/post/1"


def test_conector_google_news_se_salta_urls_ya_conocidas(monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "app.pipeline.ingesta.google_news.resolver_y_extraer",
        lambda url: llamadas.append(url) or (url, "Texto del artículo."),
    )
    conector = ConectorGoogleNews(
        consultas=[{"q": "x", "idiomas": ["es-ES"]}],
        pausa_segundos=0,
        urls_conocidas={"https://example.com/post/1"},
    )
    conector.urls = [FEED_XML]

    items = conector.fetch()

    # post/1 ya era conocida: ni se decodifica/extrae ni aparece en el resultado.
    assert llamadas == ["https://example.com/post/2"]
    assert [item.url_original for item in items] == ["https://example.com/post/2"]


def test_conector_google_news_cae_al_resumen_limpio_si_no_se_puede_extraer(monkeypatch):
    monkeypatch.setattr(
        "app.pipeline.ingesta.google_news.resolver_y_extraer", lambda url: (url, None)
    )
    conector = ConectorGoogleNews(consultas=[{"q": "x", "idiomas": ["es-ES"]}], pausa_segundos=0)
    conector.urls = [FEED_XML]

    items = conector.fetch()

    assert len(items) == 2
    assert "Ojalá existiera una app que hiciera X" in items[0].contenido_bruto


FEED_XML_HTML = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item>
  <title>Un titular cualquiera</title>
  <link>https://news.google.com/rss/articles/algo</link>
  <description>&lt;a href="https://news.google.com/rss/articles/algo"&gt;Un titular cualquiera&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;El Medio&lt;/font&gt;</description>
</item>
</channel></rss>
"""


def test_conector_google_news_limpia_el_html_del_resumen_de_fallback(monkeypatch):
    monkeypatch.setattr(
        "app.pipeline.ingesta.google_news.resolver_y_extraer", lambda url: (url, None)
    )
    conector = ConectorGoogleNews(consultas=[{"q": "x", "idiomas": ["es-ES"]}], pausa_segundos=0)
    conector.urls = [FEED_XML_HTML]

    items = conector.fetch()

    assert len(items) == 1
    assert "<a href" not in items[0].contenido_bruto
    assert "<font" not in items[0].contenido_bruto
    assert "El Medio" in items[0].contenido_bruto
