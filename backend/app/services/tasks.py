from app.core.actors import require_owner, require_participant, require_role, require_student
from app.core.errors import BusinessError
from app.models.entities import Estado, Tarea, Comentario, ACTIVOS
from app.repositories import tasks as repo
from app.schemas.contracts import TareaResult, TareasResult, EstudianteOut, EstudiantesResult, ComentarioResult
from app.schemas.serialization import tarea_out, comentario_out


def require_state(task, *states):
    if task.estado not in states:
        raise BusinessError(409, 'estado_incompatible', 'La operación no está permitida en el estado actual')


def assign_fields(task, data):
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == 'presupuesto':
            task.presupuesto_centavos = int(value * 100) if value is not None else None
        else:
            setattr(task, field, value)


class TaskService:
    def __init__(self, db):
        self.db = db

    def create(self, actor, data):
        require_role(actor, 'solicitante')
        with self.db.uow(write=True) as session:
            repo.require_subject(session, data.materia_id)
            task = Tarea(solicitante_id=actor.id, estado=Estado.BORRADOR)
            assign_fields(task, data)
            session.add(task)
            session.flush()
            session.refresh(task)
            return TareaResult(mensaje='Borrador creado', tarea=tarea_out(task))

    def update(self, actor, task_id, data):
        with self.db.uow(write=True) as session:
            task = repo.get_task(session, task_id)
            require_owner(task, actor)
            require_state(task, Estado.BORRADOR)
            repo.require_subject(session, data.materia_id)
            assign_fields(task, data)
            session.flush()
            session.refresh(task)
            return TareaResult(mensaje='Borrador actualizado', tarea=tarea_out(task))

    def detail(self, actor, task_id):
        with self.db.uow() as session:
            task = repo.get_task(session, task_id)
            require_participant(task, actor)
            return tarea_out(task)

    def list(self, actor):
        require_role(actor, 'solicitante')
        with self.db.uow() as session:
            tasks = [tarea_out(task, detail=False) for task in repo.list_tasks(session, actor.id)]
            return TareasResult(items=tasks, total=len(tasks))

    def available(self, actor, subject_id):
        with self.db.uow() as session:
            repo.require_subject(session, subject_id)
            students = [EstudianteOut.model_validate(s) for s in repo.available_students(session, subject_id)]
            return EstudiantesResult(items=students, total=len(students))

    def publish(self, actor, task_id):
        with self.db.uow(write=True) as session:
            task = repo.get_task(session, task_id)
            require_owner(task, actor)
            require_state(task, Estado.BORRADOR)
            fields = {'titulo': task.titulo, 'materia_id': task.materia_id,
                      'fecha_limite': task.fecha_limite, 'descripcion': task.descripcion,
                      'presupuesto': task.presupuesto_centavos}
            missing = [k for k, v in fields.items() if v is None]
            if missing:
                raise BusinessError(422, 'campos_faltantes', 'Completa los campos obligatorios',
                                    missing=missing, task_id=task.id, state=task.estado.value)
            task.estado = Estado.PENDIENTE
            students = repo.available_students(session, task.materia_id)
            if students:
                student = students[0]
                task.estudiante_id = student.id
                task.estado = Estado.ASIGNADA
                student.disponible = False
            session.flush()
            session.refresh(task)
            return TareaResult(mensaje='Tarea publicada', tarea=tarea_out(task))

    def transition(self, actor, task_id, action):
        with self.db.uow(write=True) as session:
            task = repo.get_task(session, task_id)
            if action in {'iniciar', 'enviar-revision'}:
                require_student(task, actor)
            else:
                require_owner(task, actor)
            if action == 'iniciar':
                require_state(task, Estado.ASIGNADA)
                task.estado = Estado.DESARROLLO
            elif action == 'enviar-revision':
                require_state(task, Estado.DESARROLLO)
                task.estado = Estado.REVISION
            elif action == 'finalizar':
                require_state(task, Estado.REVISION)
                task.estado = Estado.FINALIZADA
                task.estudiante.disponible = True
            elif action == 'cancelar':
                require_state(task, Estado.BORRADOR, Estado.PENDIENTE, *ACTIVOS)
                task.estado = Estado.CANCELADA
                if task.estudiante is not None:
                    task.estudiante.disponible = True
            else:
                raise ValueError('Acción interna desconocida')
            session.flush()
            session.refresh(task)
            return TareaResult(mensaje='Estado actualizado', tarea=tarea_out(task))

    def comment(self, actor, task_id, data):
        with self.db.uow(write=True) as session:
            task = repo.get_task(session, task_id)
            require_participant(task, actor)
            if data.requiere_correccion:
                require_state(task, Estado.DESARROLLO, Estado.REVISION)
                task.estado = Estado.REVISION
            comment = Comentario(tarea_id=task.id, contenido=data.contenido,
                                 requiere_correccion=data.requiere_correccion,
                                 autor_solicitante_id=actor.id if actor.rol == 'solicitante' else None,
                                 autor_estudiante_id=actor.id if actor.rol == 'estudiante' else None)
            session.add(comment)
            session.flush()
            session.refresh(comment)
            return ComentarioResult(mensaje='Comentario registrado', tarea_id=task.id,
                                    estado=task.estado, comentario=comentario_out(comment))
