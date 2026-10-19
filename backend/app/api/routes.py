from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, Query, Request, UploadFile

from app.core.actors import Actor, current_actor
from app.schemas.contracts import (TareaInput, TareaResult, TareaDetalle, TareasResult,
                                  EstudiantesResult, ComentarioInput, ComentarioResult, ArchivosResult)
from app.services.tasks import TaskService
from app.services.uploads import FileStorage, UploadService

router = APIRouter()
ActorDep = Annotated[Actor, Depends(current_actor)]
TaskId = Annotated[int, Path(gt=0)]


def service(request: Request):
    return TaskService(request.app.state.db)


ServiceDep = Annotated[TaskService, Depends(service)]


@router.post('/tareas', response_model=TareaResult, status_code=201, tags=['Tareas'])
def create_task(data: TareaInput, actor: ActorDep, tasks: ServiceDep):
    return tasks.create(actor, data)


@router.put('/tareas/{id}', response_model=TareaResult, tags=['Tareas'])
def update_task(id: TaskId, data: TareaInput, actor: ActorDep, tasks: ServiceDep):
    return tasks.update(actor, id, data)


@router.get('/tareas/{id}', response_model=TareaDetalle, tags=['Tareas'])
def task_detail(id: TaskId, actor: ActorDep, tasks: ServiceDep):
    return tasks.detail(actor, id)


@router.get('/tareas', response_model=TareasResult, tags=['Tareas'])
def own_tasks(actor: ActorDep, tasks: ServiceDep):
    return tasks.list(actor)


@router.get('/estudiantes', response_model=EstudiantesResult, tags=['Estudiantes'])
def available_students(actor: ActorDep, tasks: ServiceDep, materia: Annotated[int, Query(gt=0)]):
    return tasks.available(actor, materia)


@router.put('/tareas/{id}/publicar', response_model=TareaResult, tags=['Tareas'])
def publish_task(id: TaskId, actor: ActorDep, tasks: ServiceDep):
    return tasks.publish(actor, id)


@router.put('/tareas/{id}/iniciar', response_model=TareaResult, tags=['Tareas'])
def start_task(id: TaskId, actor: ActorDep, tasks: ServiceDep):
    return tasks.transition(actor, id, 'iniciar')


@router.put('/tareas/{id}/enviar-revision', response_model=TareaResult, tags=['Tareas'])
def review_task(id: TaskId, actor: ActorDep, tasks: ServiceDep):
    return tasks.transition(actor, id, 'enviar-revision')


@router.put('/tareas/{id}/finalizar', response_model=TareaResult, tags=['Tareas'])
def finish_task(id: TaskId, actor: ActorDep, tasks: ServiceDep):
    return tasks.transition(actor, id, 'finalizar')


@router.put('/tareas/{id}/cancelar', response_model=TareaResult, tags=['Tareas'])
def cancel_task(id: TaskId, actor: ActorDep, tasks: ServiceDep):
    return tasks.transition(actor, id, 'cancelar')


@router.post('/tareas/{id}/comentarios', response_model=ComentarioResult, status_code=201, tags=['Comentarios'])
def comment_task(id: TaskId, data: ComentarioInput, actor: ActorDep, tasks: ServiceDep):
    return tasks.comment(actor, id, data)


@router.post('/tareas/{id}/archivos', response_model=ArchivosResult, status_code=201, tags=['Archivos'])
def upload_files(id: TaskId, actor: ActorDep, request: Request, archivos: Annotated[list[UploadFile], File()]):
    return UploadService(request.app.state.db, FileStorage(request.app.state.settings)).upload(actor, id, archivos)
