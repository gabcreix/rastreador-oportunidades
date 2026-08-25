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


def test_conector_google_news_construye_urls_de_busqueda():
    conector = ConectorGoogleNews(consultas=["ingeniería de datos", "fintech"])

    assert len(conector.urls) == 2
    assert conector.urls[0].startswith("https://news.google.com/rss/search?q=")
    assert "hl=es-ES" in conector.urls[0]
    assert "ceid=ES:es" in conector.urls[0]
