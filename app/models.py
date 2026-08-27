from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel


class TipoOportunidad(str, Enum):
    MEJORAR = "mejorar"
    HUECO = "hueco"
    INVERSION = "inversion"


class CapaDeteccion(str, Enum):
    EXPLICITA = "explicita"
    INFERIDA = "inferida"


class EstadoOportunidad(str, Enum):
    NUEVA = "nueva"
    GUARDADA = "guardada"
    DESCARTADA = "descartada"
    EN_SEGUIMIENTO = "en_seguimiento"
    ARCHIVADA = "archivada"
    REALIZADA = "realizada"


class EstadoProcesamiento(str, Enum):
    PENDIENTE = "pendiente"
    PROCESADA = "procesada"
    DESCARTADA = "descartada"


class OrigenRelacion(str, Enum):
    SISTEMA = "sistema"
    MANUAL = "manual"


class AccionFeedback(str, Enum):
    GUARDAR = "guardar"
    DESCARTAR = "descartar"
    MARCAR = "marcar"
    CAMBIO_ESTADO = "cambio_estado"
    RECUPERAR = "recuperar"


class OportunidadArea(SQLModel, table=True):
    oportunidad_id: Optional[int] = Field(default=None, foreign_key="oportunidad.id", primary_key=True)
    area_id: Optional[int] = Field(default=None, foreign_key="area.id", primary_key=True)


class PerfilArea(SQLModel, table=True):
    perfil_id: Optional[int] = Field(default=None, foreign_key="perfil.id", primary_key=True)
    area_id: Optional[int] = Field(default=None, foreign_key="area.id", primary_key=True)


class Area(SQLModel, table=True):
    """E5 · Área/Tema."""

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True, index=True)

    oportunidades: list["Oportunidad"] = Relationship(back_populates="areas", link_model=OportunidadArea)
    perfiles: list["Perfil"] = Relationship(back_populates="areas", link_model=PerfilArea)


class Fuente(SQLModel, table=True):
    """E2 · Fuente. `rendimiento` es derivado (se calcula a partir de Capturas/Oportunidades), no se almacena."""

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    tipo: str
    config_acceso: str
    activa: bool = True
    fecha_ultimo_rastreo: Optional[datetime] = None

    capturas: list["Captura"] = Relationship(back_populates="fuente")


class Captura(SQLModel, table=True):
    """E3 · Captura. Material en bruto; nunca se borra, solo cambia estado_procesamiento."""

    id: Optional[int] = Field(default=None, primary_key=True)
    fuente_id: int = Field(foreign_key="fuente.id")
    contenido_bruto: str
    url_original: str = Field(index=True)
    fecha_captura: datetime = Field(default_factory=datetime.utcnow)
    estado_procesamiento: EstadoProcesamiento = EstadoProcesamiento.PENDIENTE

    fuente: Optional[Fuente] = Relationship(back_populates="capturas")
    oportunidades: list["Oportunidad"] = Relationship(back_populates="captura_origen")


class Perfil(SQLModel, table=True):
    """E4 · Perfil. Instancia única del usuario."""

    id: Optional[int] = Field(default=None, primary_key=True)
    skills: str = ""
    pref_esfuerzo: str = ""
    pref_capital: str = ""
    pesos_encaje: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    retencion_dias: int = 30

    areas: list[Area] = Relationship(back_populates="perfiles", link_model=PerfilArea)


class Oportunidad(SQLModel, table=True):
    """E1 · Oportunidad. La fuente se deriva vía captura_origen, sin FK directa a Fuente."""

    id: Optional[int] = Field(default=None, primary_key=True)
    titulo: str
    descripcion: str  # la necesidad/dolor subyacente, sin solución (schema de valor v3)
    solucion_propuesta: str = ""
    evidencia_demanda: str = ""
    solucion_existente: str = ""
    tipo: TipoOportunidad
    capa: CapaDeteccion
    estado: EstadoOportunidad = EstadoOportunidad.NUEVA
    puntuacion_calidad: float = 0.0
    puntuacion_encaje: float = 0.0
    puntuacion_total: float = 0.0
    justificacion: str = ""
    notas_usuario: str = ""
    captura_origen_id: int = Field(foreign_key="captura.id")
    fecha_deteccion: datetime = Field(default_factory=datetime.utcnow)
    fecha_ultimo_estado: datetime = Field(default_factory=datetime.utcnow)
    fecha_descarte: Optional[datetime] = None
    fecha_expiracion: Optional[datetime] = None

    captura_origen: Optional[Captura] = Relationship(back_populates="oportunidades")
    areas: list[Area] = Relationship(back_populates="oportunidades", link_model=OportunidadArea)
    eventos: list["EventoFeedback"] = Relationship(back_populates="oportunidad")

    relaciones_como_a: list["Relacion"] = Relationship(
        back_populates="oportunidad_a",
        sa_relationship_kwargs={"foreign_keys": "Relacion.oportunidad_a_id"},
    )
    relaciones_como_b: list["Relacion"] = Relationship(
        back_populates="oportunidad_b",
        sa_relationship_kwargs={"foreign_keys": "Relacion.oportunidad_b_id"},
    )


class Relacion(SQLModel, table=True):
    """E6 · Relación entre dos oportunidades. Estructura lista; el cálculo automático es F7 (post-MVP)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    oportunidad_a_id: int = Field(foreign_key="oportunidad.id")
    oportunidad_b_id: int = Field(foreign_key="oportunidad.id")
    tipo_relacion: str
    origen: OrigenRelacion = OrigenRelacion.SISTEMA

    oportunidad_a: Optional[Oportunidad] = Relationship(
        back_populates="relaciones_como_a",
        sa_relationship_kwargs={"foreign_keys": "Relacion.oportunidad_a_id"},
    )
    oportunidad_b: Optional[Oportunidad] = Relationship(
        back_populates="relaciones_como_b",
        sa_relationship_kwargs={"foreign_keys": "Relacion.oportunidad_b_id"},
    )


class EventoFeedback(SQLModel, table=True):
    """E7 · Evento de feedback. Se guarda pero el MVP aún no lo usa para ajustar puntuaciones (F7, post-MVP)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    oportunidad_id: int = Field(foreign_key="oportunidad.id")
    accion: AccionFeedback
    estado_resultante: str
    fecha_hora: datetime = Field(default_factory=datetime.utcnow)

    oportunidad: Optional[Oportunidad] = Relationship(back_populates="eventos")
