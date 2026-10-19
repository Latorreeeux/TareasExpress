import argparse
import json
import sys
from pathlib import Path

from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.db.database import Database
from app.models.entities import Solicitante, Estudiante, Materia
from app.schemas.contracts import Contract, PositiveId


class SeedPerson(Contract):
    id: PositiveId
    nombre: str = Field(min_length=1, max_length=200)
    correo: str = Field(min_length=3, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


class SeedStudent(SeedPerson):
    materia_ids: list[PositiveId] = Field(min_length=1)


class SeedSubject(Contract):
    id: PositiveId
    nombre: str = Field(min_length=1, max_length=200)


class SeedData(Contract):
    solicitantes: list[SeedPerson]
    estudiantes: list[SeedStudent]
    materias: list[SeedSubject]

    @model_validator(mode='after')
    def unique_references(self):
        for group in [self.solicitantes, self.estudiantes, self.materias]:
            if len({x.id for x in group}) != len(group):
                raise ValueError('IDs repetidos')
            values = [x.correo if hasattr(x, 'correo') else x.nombre for x in group]
            if len(set(values)) != len(values):
                raise ValueError('Correos o materias repetidos')
        subjects = {x.id for x in self.materias}
        for student in self.estudiantes:
            if len(set(student.materia_ids)) != len(student.materia_ids) or not set(student.materia_ids) <= subjects:
                raise ValueError('Especialidades repetidas o no incluidas en materias')
        return self


def seed(db: Database, data: SeedData):
    with db.uow(write=True) as session:
        for model, group in [(Materia, data.materias), (Solicitante, data.solicitantes), (Estudiante, data.estudiantes)]:
            for item in group:
                fields = item.model_dump(exclude={'materia_ids'})
                existing = session.get(model, item.id)
                if existing:
                    if any(getattr(existing, k) != v for k, v in fields.items()):
                        raise ValueError(f'Conflicto en {model.__tablename__}, id {item.id}')
                    if isinstance(item, SeedStudent) and set(item.materia_ids) != {m.id for m in existing.materias}:
                        raise ValueError(f'Conflicto en especialidades del estudiante {item.id}')
                else:
                    unique_column = model.nombre if model is Materia else model.correo
                    unique_value = item.nombre if model is Materia else item.correo
                    if session.scalar(select(model.id).where(unique_column == unique_value)) is not None:
                        raise ValueError(f'Valor único en conflicto en {model.__tablename__}')
                    existing = model(**fields)
                    if isinstance(item, SeedStudent):
                        existing.materias = [session.get(Materia, mid) for mid in item.materia_ids]
                    session.add(existing)
                    session.flush()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Datos locales de Tareas Express')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init-db')
    load = commands.add_parser('seed')
    load.add_argument('--file', required=True, type=Path)
    args = parser.parse_args(argv)
    db = None
    try:
        db = Database(Settings())
        if args.command == 'init-db':
            db.initialize()
            print('Esquema local inicializado')
        else:
            data = SeedData.model_validate_json(args.file.read_bytes())
            seed(db, data)
            print('Datos de referencia cargados')
        return 0
    except (ValueError, OSError, SQLAlchemyError) as exc:
        print(f'No se pudo completar {args.command}: {exc if isinstance(exc, ValueError) else "comprueba la base y los archivos locales"}', file=sys.stderr)
        return 1
    finally:
        if db:
            db.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
