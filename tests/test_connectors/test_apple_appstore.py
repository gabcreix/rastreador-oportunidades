from app.pipeline.ingesta.apple_appstore import ConectorAppleAppStore

URL_PAGINA_1 = "https://itunes.apple.com/es/rss/customerreviews/page=1/sortBy=mostRecent/id=999/json"
URL_PAGINA_2 = "https://itunes.apple.com/es/rss/customerreviews/page=2/sortBy=mostRecent/id=999/json"


def test_apple_conector_para_al_agotar_resenas(httpx_mock):
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
                    "title": {"label": "Meh"},
                    "content": {"label": "Podría mejorar"},
                    "im:rating": {"label": "3"},
                },
            ]
        }
    }
    # Página 2: solo metadata de la app, sin reseñas (sin "im:rating") -> corta aquí.
    pagina_2 = {"feed": {"entry": [{"im:name": {"label": "La App"}}]}}

    httpx_mock.add_response(url=URL_PAGINA_1, json=pagina_1)
    httpx_mock.add_response(url=URL_PAGINA_2, json=pagina_2)

    conector = ConectorAppleAppStore(app_ids=["999"], paises=["es"], pausa_segundos=0)
    items = conector.fetch()

    assert len(items) == 2
    assert items[0].url_original == "https://apple.com/review/1"
    assert "Se cuelga siempre" in items[0].contenido_bruto
    assert "1★" in items[0].contenido_bruto


def test_apple_conector_corta_en_403(httpx_mock):
    httpx_mock.add_response(url=URL_PAGINA_1, status_code=403)

    conector = ConectorAppleAppStore(app_ids=["999"], paises=["es"], pausa_segundos=0)
    items = conector.fetch()

    assert items == []
