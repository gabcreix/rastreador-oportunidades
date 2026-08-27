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


def test_resolver_y_extraer_devuelve_el_texto_principal(httpx_mock):
    httpx_mock.add_response(url="https://medio.example/noticia", html=HTML_ARTICULO)

    texto = resolver_y_extraer("https://medio.example/noticia")

    assert texto is not None
    assert "primer párrafo del artículo" in texto


def test_resolver_y_extraer_devuelve_none_si_falla_la_peticion(httpx_mock):
    httpx_mock.add_response(url="https://medio.example/rota", status_code=500)

    assert resolver_y_extraer("https://medio.example/rota") is None


def test_resolver_y_extraer_devuelve_none_ante_error_de_red(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectTimeout("fallo de red"), url="https://medio.example/timeout")

    assert resolver_y_extraer("https://medio.example/timeout") is None
