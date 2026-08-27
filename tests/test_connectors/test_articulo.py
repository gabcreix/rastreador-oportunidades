import httpx

from app.pipeline.ingesta.articulo import resolver_y_extraer

HTML_ARTICULO = """
<html><head><title>Un artículo de prueba</title></head>
<body>
<article>
<h1>Un artículo de prueba</h1>
<p>Este es el primer párrafo del artículo, con contenido real y suficientemente largo
como para que trafilatura lo reconozca como el cuerpo principal del texto.</p>
<p>Y este es un segundo párrafo que añade más contexto sobre el tema tratado, para
que la extracción tenga margen de sobra.</p>
</article>
</body></html>
"""


def test_resolver_y_extraer_devuelve_el_texto_principal_para_una_url_normal(httpx_mock):
    httpx_mock.add_response(url="https://medio.example/noticia", html=HTML_ARTICULO)

    url_final, texto = resolver_y_extraer("https://medio.example/noticia")

    assert url_final == "https://medio.example/noticia"
    assert texto is not None
    assert "primer párrafo del artículo" in texto


def test_resolver_y_extraer_devuelve_none_si_falla_la_peticion(httpx_mock):
    httpx_mock.add_response(url="https://medio.example/rota", status_code=500)

    url_final, texto = resolver_y_extraer("https://medio.example/rota")

    assert url_final == "https://medio.example/rota"
    assert texto is None


def test_resolver_y_extraer_devuelve_none_ante_error_de_red(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectTimeout("fallo de red"), url="https://medio.example/timeout")

    url_final, texto = resolver_y_extraer("https://medio.example/timeout")

    assert texto is None


def test_resolver_y_extraer_decodifica_enlaces_de_google_news(monkeypatch, httpx_mock):
    monkeypatch.setattr(
        "app.pipeline.ingesta.articulo.gnewsdecoder",
        lambda url, interval=1: {"status": True, "decoded_url": "https://medio.example/real"},
    )
    httpx_mock.add_response(url="https://medio.example/real", html=HTML_ARTICULO)

    url_final, texto = resolver_y_extraer("https://news.google.com/rss/articles/CBMi...")

    assert url_final == "https://medio.example/real"
    assert texto is not None


def test_resolver_y_extraer_usa_url_original_si_falla_la_decodificacion(monkeypatch, httpx_mock):
    monkeypatch.setattr(
        "app.pipeline.ingesta.articulo.gnewsdecoder",
        lambda url, interval=1: {"status": False, "message": "no se pudo decodificar"},
    )
    httpx_mock.add_response(url="https://news.google.com/rss/articles/CBMi...", status_code=404)

    url_final, texto = resolver_y_extraer("https://news.google.com/rss/articles/CBMi...")

    assert url_final == "https://news.google.com/rss/articles/CBMi..."
    assert texto is None
