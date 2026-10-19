from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import select

from app.models.entities import Estudiante, Tarea, ACTIVOS
from conftest import headers, draft


def concurrent_publish(client, ids):
    barrier = Barrier(2)
    def publish(tid):
        barrier.wait(timeout=5)
        return client.put(f'/tareas/{tid}/publicar', headers=headers())
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(publish, tid) for tid in ids]
        return [f.result(timeout=10) for f in futures]


def test_two_publications_one_student(api):
    client, app = api
    first, second = draft(client), draft(client)
    # Una conexión de lectura queda abierta para asegurar conexiones independientes.
    with app.state.db.engine.connect() as held:
        responses = concurrent_publish(client, [first, second])
    assert [r.status_code for r in responses] == [200, 200]
    assert sorted(r.json()['tarea']['estado'] for r in responses) == ['asignada', 'pendiente_asignacion']
    with app.state.db.uow() as session:
        active = session.scalars(select(Tarea).where(Tarea.estado.in_(ACTIVOS))).unique().all()
        assert len(active) == 1 and active[0].estudiante_id == 1
        assert not session.get(Estudiante, 1).disponible


def test_same_task_concurrent_publication(api):
    client, app = api
    tid = draft(client)
    responses = concurrent_publish(client, [tid, tid])
    assert sorted(r.status_code for r in responses) == [200, 409]
    with app.state.db.uow() as session:
        assert session.get(Tarea, tid).estudiante_id == 1
        assert not session.get(Estudiante, 1).disponible
