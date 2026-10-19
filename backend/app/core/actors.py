from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Header, Request

from app.core.errors import BusinessError
from app.models.entities import Solicitante, Estudiante


@dataclass(frozen=True)
class Actor:
    rol: str
    id: int


def current_actor(request: Request,
                  role: Annotated[Literal['solicitante', 'estudiante'] | None, Header(alias='X-Actor-Rol')] = None,
                  actor_id: Annotated[int | None, Header(alias='X-Actor-Id', gt=0)] = None) -> Actor:
    if role is None or actor_id is None:
        raise BusinessError(401, 'identidad_requerida', 'Faltan cabeceras de identidad local')
    with request.app.state.db.uow() as session:
        model = Solicitante if role == 'solicitante' else Estudiante
        if session.get(model, actor_id) is None:
            raise BusinessError(401, 'identidad_desconocida', 'Actor no registrado')
    return Actor(role, actor_id)


def require_role(actor: Actor, role: str):
    if actor.rol != role:
        raise BusinessError(403, 'sin_permiso', 'El actor no puede realizar esta operación')


def require_owner(task, actor: Actor):
    if actor.rol != 'solicitante' or task.solicitante_id != actor.id:
        raise BusinessError(403, 'sin_permiso', 'Se requiere el solicitante de la tarea')


def require_student(task, actor: Actor):
    if actor.rol != 'estudiante' or task.estudiante_id != actor.id:
        raise BusinessError(403, 'sin_permiso', 'Se requiere el estudiante asignado')


def require_participant(task, actor: Actor):
    if not ((actor.rol == 'solicitante' and task.solicitante_id == actor.id)
            or (actor.rol == 'estudiante' and task.estudiante_id == actor.id)):
        raise BusinessError(403, 'sin_permiso', 'El actor no participa en la tarea')
