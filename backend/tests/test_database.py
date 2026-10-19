import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.db.database import Database
from app.models.entities import Solicitante, Estudiante, Tarea, Estado, Materia, Comentario


@pytest.fixture
def db(tmp_path):
    result = Database(Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'test.db'}", upload_dir=tmp_path / 'uploads'))
    result.initialize()
    with result.uow(write=True) as s:
        s.add_all([Solicitante(id=1, nombre="Uno", correo="uno@example.test"),
                   Estudiante(id=1, nombre="Estudiante", correo="e@example.test"), Materia(id=1, nombre="Matemáticas")])
    yield result
    result.dispose()


def test_pragmas_and_rollback(db):
    for _ in range(2):
        with db.uow() as s:
            assert s.scalar(text('PRAGMA foreign_keys')) == 1
            assert s.scalar(text('PRAGMA journal_mode')) == 'wal'
            assert s.scalar(text('PRAGMA busy_timeout')) == 5000
    with pytest.raises(RuntimeError):
        with db.uow(write=True) as s:
            s.add(Materia(id=2, nombre="Historia"))
            s.flush()
            raise RuntimeError('fallo')
    with db.uow() as s:
        assert s.get(Materia, 2) is None


def test_active_unique_and_history(db):
    with db.uow(write=True) as s:
        s.add(Tarea(solicitante_id=1, estudiante_id=1, estado=Estado.ASIGNADA))
    with pytest.raises(IntegrityError):
        with db.uow(write=True) as s:
            s.add(Tarea(solicitante_id=1, estudiante_id=1, estado=Estado.REVISION))
    with db.uow(write=True) as s:
        s.add_all([Tarea(solicitante_id=1, estudiante_id=1, estado=Estado.FINALIZADA),
                   Tarea(solicitante_id=1, estudiante_id=1, estado=Estado.CANCELADA)])
    assert 'uq_estudiante_tarea_activa' in {i['name'] for i in inspect(db.engine).get_indexes('tareas')}


@pytest.mark.parametrize('values', [
    {'solicitante_id': 999}, {'solicitante_id': 1, 'presupuesto_centavos': -1},
    {'solicitante_id': 1, 'presupuesto_centavos': 1000000000000},
    {'solicitante_id': 1, 'estado': Estado.ASIGNADA},
    {'solicitante_id': 1, 'estado': Estado.BORRADOR, 'estudiante_id': 1},
    {'solicitante_id': 1, 'estado': 'desconocido'},
])
def test_task_constraints(db, values):
    with pytest.raises(IntegrityError):
        with db.uow(write=True) as s:
            s.add(Tarea(**values))


@pytest.mark.parametrize('authors', [{}, {'autor_solicitante_id': 1, 'autor_estudiante_id': 1}])
def test_comment_exactly_one_author(db, authors):
    with db.uow(write=True) as s:
        task = Tarea(solicitante_id=1)
        s.add(task)
        s.flush()
        task_id = task.id
    with pytest.raises(IntegrityError):
        with db.uow(write=True) as s:
            s.add(Comentario(tarea_id=task_id, contenido='Texto', **authors))
