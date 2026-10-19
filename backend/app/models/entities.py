from datetime import date, datetime, timezone
from enum import StrEnum

from sqlalchemy import (Boolean, CheckConstraint, Column, Date, DateTime, Enum,
                        ForeignKey, Index, Integer, String, Table, Text)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Estado(StrEnum):
    BORRADOR = "borrador"
    PENDIENTE = "pendiente_asignacion"
    ASIGNADA = "asignada"
    DESARROLLO = "en_desarrollo"
    REVISION = "en_revision"
    FINALIZADA = "finalizada"
    CANCELADA = "cancelada"


ACTIVOS = (Estado.ASIGNADA, Estado.DESARROLLO, Estado.REVISION)
ETIQUETAS = dict(zip(Estado, ["Borrador", "Pendiente de asignación", "Asignada", "En desarrollo", "En revisión", "Finalizada", "Cancelada"]))

especialidades = Table(
    "estudiante_materia", Base.metadata,
    Column("estudiante_id", ForeignKey("estudiantes.id"), primary_key=True),
    Column("materia_id", ForeignKey("materias.id"), primary_key=True),
    Index("ix_especialidad_materia", "materia_id"),
)


class Solicitante(Base):
    __tablename__ = "solicitantes"
    __table_args__ = (CheckConstraint("length(trim(nombre)) > 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    correo: Mapped[str] = mapped_column(String(254), unique=True)


class Estudiante(Base):
    __tablename__ = "estudiantes"
    __table_args__ = (CheckConstraint("length(trim(nombre)) > 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    correo: Mapped[str] = mapped_column(String(254), unique=True)
    disponible: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=True)
    materias: Mapped[list["Materia"]] = relationship(secondary=especialidades, lazy="selectin")


class Materia(Base):
    __tablename__ = "materias"
    __table_args__ = (CheckConstraint("length(trim(nombre)) > 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), unique=True)


class Tarea(Base):
    __tablename__ = "tareas"
    __table_args__ = (
        CheckConstraint("presupuesto_centavos IS NULL OR presupuesto_centavos BETWEEN 0 AND 999999999999"),
        CheckConstraint("(estado IN ('asignada','en_desarrollo','en_revision','finalizada') AND estudiante_id IS NOT NULL) OR (estado IN ('borrador','pendiente_asignacion') AND estudiante_id IS NULL) OR estado = 'cancelada'"),
        Index("uq_estudiante_tarea_activa", "estudiante_id", unique=True,
              sqlite_where=Column("estado").in_([e.value for e in ACTIVOS])),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    solicitante_id: Mapped[int] = mapped_column(ForeignKey("solicitantes.id"), index=True)
    materia_id: Mapped[int | None] = mapped_column(ForeignKey("materias.id"), index=True)
    estudiante_id: Mapped[int | None] = mapped_column(ForeignKey("estudiantes.id"))
    titulo: Mapped[str | None] = mapped_column(String(200))
    descripcion: Mapped[str | None] = mapped_column(Text)
    fecha_limite: Mapped[date | None] = mapped_column(Date)
    presupuesto_centavos: Mapped[int | None] = mapped_column(Integer)
    estado: Mapped[Estado] = mapped_column(Enum(Estado, native_enum=False, create_constraint=True,
        values_callable=lambda enums: [e.value for e in enums]), default=Estado.BORRADOR, index=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    actualizada_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    solicitante: Mapped[Solicitante] = relationship(lazy="joined")
    materia: Mapped[Materia | None] = relationship(lazy="joined")
    estudiante: Mapped[Estudiante | None] = relationship(lazy="joined")
    archivos: Mapped[list["Archivo"]] = relationship(lazy="selectin", order_by="Archivo.id")
    comentarios: Mapped[list["Comentario"]] = relationship(lazy="selectin", order_by="Comentario.id")


class Archivo(Base):
    __tablename__ = "archivos"
    __table_args__ = (CheckConstraint("tamano_bytes >= 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tarea_id: Mapped[int] = mapped_column(ForeignKey("tareas.id"), index=True)
    nombre_original: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(255))
    clave: Mapped[str] = mapped_column(String(64), unique=True)
    tamano_bytes: Mapped[int] = mapped_column(Integer)
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Comentario(Base):
    __tablename__ = "comentarios"
    __table_args__ = (CheckConstraint("(autor_solicitante_id IS NOT NULL AND autor_estudiante_id IS NULL) OR (autor_solicitante_id IS NULL AND autor_estudiante_id IS NOT NULL)"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tarea_id: Mapped[int] = mapped_column(ForeignKey("tareas.id"), index=True)
    contenido: Mapped[str] = mapped_column(Text)
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    requiere_correccion: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    autor_solicitante_id: Mapped[int | None] = mapped_column(ForeignKey("solicitantes.id"))
    autor_estudiante_id: Mapped[int | None] = mapped_column(ForeignKey("estudiantes.id"))
    solicitante: Mapped[Solicitante | None] = relationship(lazy="joined")
    estudiante: Mapped[Estudiante | None] = relationship(lazy="joined")
