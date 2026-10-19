from sqlalchemy import select

from app.core.errors import BusinessError
from app.models.entities import Tarea, Materia, Estudiante, especialidades, ACTIVOS


def get_task(session, task_id):
    task = session.get(Tarea, task_id)
    if task is None:
        raise BusinessError(404, 'tarea_inexistente', 'La tarea no existe')
    return task


def require_subject(session, subject_id):
    if subject_id is not None and session.get(Materia, subject_id) is None:
        raise BusinessError(404, 'materia_inexistente', 'La materia no existe')


def list_tasks(session, owner_id):
    return session.scalars(select(Tarea).where(Tarea.solicitante_id == owner_id).order_by(Tarea.id)).unique().all()


def available_students(session, subject_id):
    active = select(Tarea.id).where(Tarea.estudiante_id == Estudiante.id, Tarea.estado.in_(ACTIVOS)).exists()
    query = (select(Estudiante).join(especialidades).where(
        especialidades.c.materia_id == subject_id, Estudiante.disponible.is_(True), ~active).order_by(Estudiante.id))
    return session.scalars(query).unique().all()
