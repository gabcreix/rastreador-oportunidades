from app.models import CapaDeteccion, Captura, Fuente, TipoOportunidad
from app.pipeline.deteccion import NOMBRE_HERRAMIENTA, DetectorAnthropic


class _BloqueFalso:
    def __init__(self, oportunidades):
        self.type = "tool_use"
        self.input = {"oportunidades": oportunidades}


class _RespuestaFalsa:
    def __init__(self, oportunidades):
        self.content = [_BloqueFalso(oportunidades)]


class _MensajesFalsos:
    def __init__(self, oportunidades):
        self._oportunidades = oportunidades
        self.ultima_llamada = None

    def create(self, **kwargs):
        self.ultima_llamada = kwargs
        return _RespuestaFalsa(self._oportunidades)


class _ClienteFalso:
    def __init__(self, oportunidades):
        self.messages = _MensajesFalsos(oportunidades)


def _crear_captura(session):
    fuente = Fuente(nombre="Test", tipo="prensa", config_acceso="{}")
    session.add(fuente)
    session.commit()
    captura = Captura(fuente_id=fuente.id, contenido_bruto="algún texto de prueba", url_original="https://x.com/1")
    session.add(captura)
    session.commit()
    session.refresh(captura)
    return captura


def test_detector_parsea_oportunidades_detectadas(session):
    captura = _crear_captura(session)
    cliente_falso = _ClienteFalso(
        [
            {
                "titulo": "Buscador de empleo junior",
                "descripcion": "Los jóvenes no encuentran su primer empleo.",
                "tipo": "hueco",
                "capa": "inferida",
                "justificacion": "El artículo describe una escasez de ofertas junior.",
            }
        ]
    )
    detector = DetectorAnthropic(client=cliente_falso, model="test-model")

    candidatas = detector.detectar(captura)

    assert len(candidatas) == 1
    assert candidatas[0].titulo == "Buscador de empleo junior"
    assert candidatas[0].tipo == TipoOportunidad.HUECO
    assert candidatas[0].capa == CapaDeteccion.INFERIDA

    llamada = cliente_falso.messages.ultima_llamada
    assert llamada["model"] == "test-model"
    assert llamada["tool_choice"] == {"type": "tool", "name": NOMBRE_HERRAMIENTA}
    assert "Fuente: Test (prensa)" in llamada["messages"][0]["content"]


def test_detector_sin_oportunidades_devuelve_lista_vacia(session):
    captura = _crear_captura(session)
    cliente_falso = _ClienteFalso([])
    detector = DetectorAnthropic(client=cliente_falso, model="test-model")

    assert detector.detectar(captura) == []


def test_detector_varias_oportunidades_en_un_texto(session):
    captura = _crear_captura(session)
    cliente_falso = _ClienteFalso(
        [
            {
                "titulo": "A",
                "descripcion": "da",
                "tipo": "mejorar",
                "capa": "explicita",
                "justificacion": "ja",
            },
            {
                "titulo": "B",
                "descripcion": "db",
                "tipo": "hueco",
                "capa": "inferida",
                "justificacion": "jb",
            },
        ]
    )
    detector = DetectorAnthropic(client=cliente_falso, model="test-model")

    candidatas = detector.detectar(captura)

    assert [c.titulo for c in candidatas] == ["A", "B"]
