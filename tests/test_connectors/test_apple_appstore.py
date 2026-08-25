from app.pipeline.ingesta.apple_appstore import ConectorAppleAppStore

URL_CHART = "https://rss.marketingtools.apple.com/api/v2/us/apps/top-free/2/apps.json"
URL_RESENAS_1 = "https://itunes.apple.com/us/rss/customerreviews/page=1/sortBy=mostRecent/id=111/json"
URL_RESENAS_2 = "https://itunes.apple.com/us/rss/customerreviews/page=2/sortBy=mostRecent/id=111/json"


def _conector(**overrides):
    kwargs = dict(
        paises_charts=["us"],
        tipos_chart=["top-free"],
        limite_chart=2,
        generos_interes=["6015"],
        paises_resenas=["us"],
        paginas_resenas=2,
        pausa_segundos=0,
    )
    kwargs.update(overrides)
    return ConectorAppleAppStore(**kwargs)


def test_descubre_solo_apps_del_genero_de_interes_y_solo_resenas_negativas(httpx_mock):
    chart = {
        "feed": {
            "results": [
                {"id": "111", "name": "App Finanzas", "genres": [{"genreId": "6015"}]},
                {"id": "222", "name": "App Juegos", "genres": [{"genreId": "6014"}]},
                {"id": "333", "name": "App Sin Genero", "genres": []},
            ]
        }
    }
    pagina_1 = {
        "feed": {
            "entry": [
                {
                    "id": {"label": "https://apple.com/review/1"},
                    "title": {"label": "Va fatal"},
                    "content": {"label": "Se cuelga siempre"},
                    "im:rating": {"label": "1"},
                },
                {
                    "id": {"label": "https://apple.com/review/2"},
                    "title": {"label": "Genial"},
                    "content": {"label": "Me encanta"},
                    "im:rating": {"label": "5"},
                },
            ]
        }
    }
    pagina_2 = {"feed": {"entry": [{"im:name": {"label": "meta de la app"}}]}}

    httpx_mock.add_response(url=URL_CHART, json=chart)
    httpx_mock.add_response(url=URL_RESENAS_1, json=pagina_1)
    httpx_mock.add_response(url=URL_RESENAS_2, json=pagina_2)

    items = _conector().fetch()

    assert len(items) == 1
    assert items[0].url_original == "https://apple.com/review/1"
    assert "1★" in items[0].contenido_bruto
    assert "Se cuelga siempre" in items[0].contenido_bruto


def test_chart_roto_no_rompe_el_fetch(httpx_mock):
    httpx_mock.add_response(url=URL_CHART, status_code=500)

    items = _conector().fetch()

    assert items == []
