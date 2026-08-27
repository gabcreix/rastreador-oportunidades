from app.models import CapaDeteccion, Captura, Fuente, TipoOportunidad
from app.pipeline.deteccion import NOMBRE_HERRAMIENTA, DetectorAnthropic


class _BloqueFalso:
    def __init__(self, analisis_previo, oportunidades):
        self.type = "tool_use"
        self.input = {"analisis_previo": analisis_previo, "oportunidades": oportunidades}


class _RespuestaFalsa:
    def __init__(self, analisis_previo, oportunidades):
        self.content = [_BloqueFalso(analisis_previo, oportunidades)]


class _MensajesFalsos:
    def __init__(self, oportunidades, analisis_previo=""):
        self._oportunidades = oportunidades
        self._analisis_previo = analisis_previo
        self.ultima_llamada = None

    def create(self, **kwargs):
        self.ultima_llamada = kwargs
        return _RespuestaFalsa(self._analisis_previo, self._oportunidades)


class _ClienteFalso:
    def __init__(self, oportunidades, analisis_previo=""):
        self.messages = _MensajesFalsos(oportunidades, analisis_previo)


def _oportunidad(**overrides):
    base = {
        "titulo": "T",
        "descripcion": "D",
        "solucion_propuesta": "S",
        "tipo": "hueco",
        "capa": "inferida",
        "evidencia_demanda": "E",
        "solucion_existente": "",
        "justificacion": "J",
    }
    base.update(overrides)
    return base


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
            _oportunidad(
                titulo="Buscador de empleo junior",
                descripcion="Los jóvenes no encuentran su primer empleo.",
                solucion_propuesta="Bolsa de empleo filtrada a primer empleo.",
                tipo="hueco",
                capa="inferida",
                evidencia_demanda="Reportaje describe fricción de un colectivo amplio.",
                solucion_existente="Portales generalistas, no especializados.",
            )
        ],
        analisis_previo="Se deduce un hueco concreto y construible.",
    )
    detector = DetectorAnthropic(client=cliente_falso, model="test-model")

    candidatas = detector.detectar(captura)

    assert len(candidatas) == 1
    candidata = candidatas[0]
    assert candidata.titulo == "Buscador de empleo junior"
    assert candidata.solucion_propuesta == "Bolsa de empleo filtrada a primer empleo."
    assert candidata.evidencia_demanda == "Reportaje describe fricción de un colectivo amplio."
    assert candidata.solucion_existente == "Portales generalistas, no especializados."
    assert candidata.tipo == TipoOportunidad.HUECO
    assert candidata.capa == CapaDeteccion.INFERIDA

    llamada = cliente_falso.messages.ultima_llamada
    assert llamada["model"] == "test-model"
    assert llamada["max_tokens"] == 2048
    assert llamada["tool_choice"] == {"type": "tool", "name": NOMBRE_HERRAMIENTA}
    assert "Fuente: Test (prensa)" in llamada["messages"][0]["content"]


def test_detector_sin_oportunidades_devuelve_lista_vacia(session):
    captura = _crear_captura(session)
    cliente_falso = _ClienteFalso([], analisis_previo="Desahogo personal, no hay necesidad de producto. No reportar.")
    detector = DetectorAnthropic(client=cliente_falso, model="test-model")

    assert detector.detectar(captura) == []


def test_detector_varias_oportunidades_en_un_texto(session):
    captura = _crear_captura(session)
    cliente_falso = _ClienteFalso(
        [
            _oportunidad(titulo="A", tipo="mejorar", capa="explicita"),
            _oportunidad(titulo="B", tipo="hueco", capa="inferida"),
        ]
    )
    detector = DetectorAnthropic(client=cliente_falso, model="test-model")

    candidatas = detector.detectar(captura)

    assert [c.titulo for c in candidatas] == ["A", "B"]
