import httpx
import trafilatura
from googlenewsdecoder import gnewsdecoder

_UA = "RastreadorOportunidades/1.0 (proyecto personal; contacto: gabcreix@gmail.com)"
_TIMEOUT = 15.0


def _resolver_url_real(url: str) -> str:
    """Los enlaces de Google News no son una redirección HTTP normal: la
    resolución final la hace JavaScript vía una llamada interna de Google
    (batchexecute), así que un simple `follow_redirects` no basta. Si es un
    enlace de Google News, lo decodifica a la URL real del medio; si no lo
    es, o falla la decodificación, devuelve la URL tal cual.
    """
    if "news.google.com" not in url:
        return url
    try:
        resultado = gnewsdecoder(url, interval=1)
        if resultado.get("status") and resultado.get("decoded_url"):
            return resultado["decoded_url"]
    except Exception:
        pass
    return url


def resolver_y_extraer(url: str) -> tuple[str, str | None]:
    """Resuelve redirecciones (p. ej. Google News → medio) y extrae el texto
    principal del artículo. Devuelve (url_final, texto_o_None): el texto es
    None si no se puede extraer (el llamador cae al `summary` del RSS), pero
    url_final es casi siempre más útil que el enlace de redirección original.
    Nunca debe tumbar el rastreo de la fuente.
    """
    url_final = _resolver_url_real(url)
    try:
        with httpx.Client(
            follow_redirects=True, timeout=_TIMEOUT, headers={"User-Agent": _UA}
        ) as cliente:
            respuesta = cliente.get(url_final)
            respuesta.raise_for_status()
            texto = trafilatura.extract(
                respuesta.text,
                include_comments=False,
                include_tables=False,
                favor_precision=True,
            )
            return url_final, ((texto or "").strip() or None)
    except Exception:
        return url_final, None
