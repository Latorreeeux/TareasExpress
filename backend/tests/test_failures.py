from pathlib import Path

import pytest
from sqlalchemy import event, select, func

from app.models.entities import Tarea, Estudiante, Comentario, Archivo, Estado
from app.services.uploads import FileStorage
from conftest import headers, draft
from test_lifecycle import action
from test_uploads import send


def fail_commit(engine):
    def broken(connection):
        # La resolución del actor usa otra transacción de lectura. Fallar solo
        # después de ejecutar la unidad de escritura real que estamos comprobando.
        if connection.get_execution_options().get('write_transaction'):
            broken.triggered = True
            raise RuntimeError('fallo privado de commit')
    broken.triggered = False
    event.listen(engine, 'commit', broken)
    return broken


def test_publication_commit_failure_rolls_back(api):
    client, app = api
    tid = draft(client)
    listener = fail_commit(app.state.db.engine)
    try:
        response = action(client, tid, 'publicar')
        assert response.status_code == 500
        assert listener.triggered
        assert 'privado' not in response.text and 'Traceback' not in response.text
    finally:
        event.remove(app.state.db.engine, 'commit', listener)
    with app.state.db.uow() as session:
        task = session.get(Tarea, tid)
        assert task.estado == Estado.BORRADOR and task.estudiante_id is None
        assert session.get(Estudiante, 1).disponible


@pytest.mark.parametrize('operation', ['finalizar', 'cancelar', 'comentario'])
def test_transition_commit_failure_rolls_back(api, operation):
    client, app = api
    tid = draft(client)
    action(client, tid, 'publicar')
    action(client, tid, 'iniciar', 'estudiante')
    if operation == 'finalizar':
        action(client, tid, 'enviar-revision', 'estudiante')
    before = client.get(f'/tareas/{tid}', headers=headers()).json()['estado']
    listener = fail_commit(app.state.db.engine)
    try:
        if operation == 'comentario':
            response = client.post(f'/tareas/{tid}/comentarios', headers=headers(), json={'contenido': 'Corregir', 'requiere_correccion': True})
        else:
            response = action(client, tid, operation)
        assert response.status_code == 500
        assert listener.triggered
    finally:
        event.remove(app.state.db.engine, 'commit', listener)
    with app.state.db.uow() as session:
        assert session.get(Tarea, tid).estado.value == before
        assert not session.get(Estudiante, 1).disponible
        assert session.scalar(select(func.count()).select_from(Comentario)) == 0


def test_sqlite_busy_response(api):
    client, app = api
    tid = draft(client)
    # Configuración de nuevas conexiones con timeout breve, sin cambiar semántica.
    app.state.settings.sqlite_busy_timeout_ms = 40
    app.state.db.engine.dispose()
    with app.state.db.uow(write=True) as session:
        session.get(Tarea, tid)  # BEGIN IMMEDIATE mantiene el bloqueo.
        response = action(client, tid, 'publicar')
        assert response.status_code == 503, response.text
        assert response.json()['error']['codigo'] == 'base_ocupada'
    with app.state.db.uow() as session:
        assert session.get(Tarea, tid).estado == Estado.BORRADOR
        assert session.get(Estudiante, 1).disponible


@pytest.mark.parametrize('failure', ['move', 'write', 'commit'])
def test_upload_failures_compensate_without_touching_existing(api, monkeypatch, failure):
    client, app = api
    tid = draft(client)
    previous = send(client, tid).json()['archivos'][0]
    root = app.state.settings.upload_dir
    listener = None
    if failure == 'commit':
        listener = fail_commit(app.state.db.engine)
    elif failure == 'move':
        original = FileStorage.move
        calls = []
        def broken(self, item):
            calls.append(True)
            if len(calls) == 2:
                raise OSError('fallo mover')
            return original(self, item)
        monkeypatch.setattr(FileStorage, 'move', broken)
    else:
        original = Path.open
        calls = []
        def broken(path, mode='r', *args, **kwargs):
            if mode == 'xb':
                calls.append(True)
                if len(calls) == 2:
                    raise OSError('fallo escribir')
            return original(path, mode, *args, **kwargs)
        monkeypatch.setattr(Path, 'open', broken)
    try:
        response = send(client, tid, [('archivos', ('1', b'a')), ('archivos', ('2', b'b'))])
        assert response.status_code == 500, response.text
        if listener:
            assert listener.triggered
    finally:
        if listener:
            event.remove(app.state.db.engine, 'commit', listener)
    assert sorted(p.name for p in root.rglob('*') if p.is_file()) == [previous['ubicacion']]
    assert (root / previous['ubicacion']).read_bytes() == b'hola'
    with app.state.db.uow() as session:
        assert session.scalar(select(func.count()).select_from(Archivo)) == 1
