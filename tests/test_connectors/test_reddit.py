from app.pipeline.ingesta.reddit import ConectorReddit

NEW_FEED_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>Idea de sub</title><link>https://reddit.com/post/1</link><description>desc</description></item>
</channel></rss>
"""

SEARCH_FEED_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>Resultado búsqueda</title><link>https://reddit.com/post/2</link><description>desc</description></item>
</channel></rss>
"""


def test_url_busqueda_global_usa_quote_plus_y_sort_new():
    url = ConectorReddit._url_busqueda({"q": '("someone should build") self:true', "scope": "global"})

    assert url.startswith("https://www.reddit.com/search.rss?q=")
    assert "self%3Atrue" in url
    assert "sort=new" in url


def test_url_busqueda_subreddit_incluye_restrict_sr():
    url = ConectorReddit._url_busqueda(
        {"q": "alguna consulta", "scope": "subreddit", "subs": "SaaS+Entrepreneur"}
    )

    assert url.startswith("https://www.reddit.com/r/SaaS+Entrepreneur/search.rss?q=")
    assert "restrict_sr=1" in url


def test_fetch_combina_new_y_busquedas_y_un_403_no_tumba_el_resto(httpx_mock):
    url_new = "https://www.reddit.com/r/test/new.rss"
    consultas = [
        {"id": "Q1", "q": "primera", "scope": "global"},
        {"id": "Q2", "q": "segunda", "scope": "global"},
    ]
    url_q1 = ConectorReddit._url_busqueda(consultas[0])
    url_q2 = ConectorReddit._url_busqueda(consultas[1])

    httpx_mock.add_response(url=url_new, text=NEW_FEED_XML)
    httpx_mock.add_response(url=url_q1, status_code=403)
    httpx_mock.add_response(url=url_q2, text=SEARCH_FEED_XML)

    conector = ConectorReddit(urls_new=[url_new], consultas=consultas, pausa_segundos=0)
    items = conector.fetch()

    urls = {item.url_original for item in items}
    assert urls == {"https://reddit.com/post/1", "https://reddit.com/post/2"}


def test_429_se_reintenta_y_no_se_da_por_vencido_a_la_primera(httpx_mock):
    url = ConectorReddit._url_busqueda({"q": "algo", "scope": "global"})
    httpx_mock.add_response(url=url, status_code=429)
    httpx_mock.add_response(url=url, text=SEARCH_FEED_XML)

    conector = ConectorReddit(urls_new=[], consultas=[{"q": "algo", "scope": "global"}], pausa_segundos=0)
    items = conector.fetch()

    assert [item.url_original for item in items] == ["https://reddit.com/post/2"]


def test_429_agota_reintentos_y_se_rinde(httpx_mock):
    url = ConectorReddit._url_busqueda({"q": "algo", "scope": "global"})
    httpx_mock.add_response(url=url, status_code=429)
    httpx_mock.add_response(url=url, status_code=429)

    conector = ConectorReddit(
        urls_new=[], consultas=[{"q": "algo", "scope": "global"}], pausa_segundos=0, reintentos_429=1
    )
    items = conector.fetch()

    assert items == []
