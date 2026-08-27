import httpx
import trafilatura

_UA = "RastreadorOportunidades/1.0 (proyecto personal; contacto: gabcreix@gmail.com)"
_TIMEOUT = 15.0


def resolver_y_extraer(url: str) -> str | None:
    """Resuelve redirecciones (p. ej. Google News → medio real) y extrae el
    texto principal del artículo. Devuelve None si no se puede (el llamador
    cae al `summary` del RSS): nunca debe tumbar el rastreo de la fuente.
    """
    try:
        with httpx.Client(
            follow_redirects=True, timeout=_TIMEOUT, headers={"User-Agent": _UA}
        ) as cliente:
            respuesta = cliente.get(url)
            respuesta.raise_for_status()
            texto = trafilatura.extract(
                respuesta.text,
                include_comments=False,
                include_tables=False,
                favor_precision=True,
            )
            return (texto or "").strip() or None
    except Exception:
        return None
