import re
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

from app.models.entities import Estado

PositiveId = Annotated[int, Field(gt=0)]
Money = Annotated[Decimal, Field(ge=0, le=Decimal('9999999999.99'), decimal_places=2, allow_inf_nan=False),
                  PlainSerializer(lambda v: format(v, '.2f'), return_type=str, when_used='json')]
Utc = Annotated[datetime, PlainSerializer(lambda v: v.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z'), return_type=str, when_used='json')]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)


class TareaInput(Contract):
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    materia_id: PositiveId | None = None
    fecha_limite: date | None = None
    descripcion: str | None = Field(default=None, min_length=1, max_length=5000)
    presupuesto: Money | None = None

    @field_validator('fecha_limite', mode='before')
    @classmethod
    def iso_date(cls, value):
        if value is not None and not (isinstance(value, date) and not isinstance(value, datetime)):
            if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError('Se requiere una fecha YYYY-MM-DD')
        return value

    @field_validator('presupuesto', mode='before')
    @classmethod
    def not_boolean_money(cls, value):
        if isinstance(value, bool):
            raise ValueError('Presupuesto inválido')
        return value


class ComentarioInput(Contract):
    contenido: str = Field(min_length=1, max_length=5000)
    requiere_correccion: bool = False


class PersonaOut(Contract):
    id: int
    nombre: str
    correo: str


class MateriaOut(Contract):
    id: int
    nombre: str


class EstudianteOut(PersonaOut):
    disponible: bool
    materias: list[MateriaOut]


class AutorOut(Contract):
    rol: Literal['solicitante', 'estudiante']
    id: int
    nombre: str


class ArchivoOut(Contract):
    id: int
    nombre: str
    tipo: str
    ubicacion: str
    tamano_bytes: int


class ComentarioOut(Contract):
    id: int
    contenido: str
    fecha: Utc
    autor: AutorOut
    requiere_correccion: bool


class TareaResumen(Contract):
    id: int
    titulo: str | None
    descripcion: str | None
    fecha_limite: date | None
    presupuesto: Money | None
    estado: Estado
    estado_descripcion: str
    solicitante: PersonaOut
    materia: MateriaOut | None
    estudiante_asignado: PersonaOut | None
    creada_en: Utc
    actualizada_en: Utc


class TareaDetalle(TareaResumen):
    archivos: list[ArchivoOut]
    comentarios: list[ComentarioOut]


class TareaResult(Contract):
    mensaje: str
    tarea: TareaDetalle


class TareasResult(Contract):
    items: list[TareaResumen]
    total: int


class EstudiantesResult(Contract):
    items: list[EstudianteOut]
    total: int


class ArchivosResult(Contract):
    mensaje: str
    tarea_id: int
    estado: Estado
    archivos: list[ArchivoOut]


class ComentarioResult(Contract):
    mensaje: str
    tarea_id: int
    estado: Estado
    comentario: ComentarioOut
