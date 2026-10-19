import pytest

from conftest import draft, headers


def action(client, tid, name, role='solicitante', actor_id=1):
    return client.put(f'/tareas/{tid}/{name}', headers=headers(role, actor_id))


def test_publish_missing_and_candidate_filters(api):
    client, _ = api
    tid = client.post('/tareas', json={}, headers=headers()).json()['tarea']['id']
    missing = action(client, tid, 'publicar')
    assert missing.status_code == 422
    assert set(missing.json()['error']['campos_faltantes']) == {'titulo', 'materia_id', 'fecha_limite', 'descripcion', 'presupuesto'}
    assert missing.json()['estado'] == 'borrador'
    assert client.get(f'/tareas/{tid}', headers=headers()).json()['estado'] == 'borrador'
    assert [s['id'] for s in client.get('/estudiantes?materia=2', headers=headers()).json()['items']] == [1, 2]
    new = draft(client, presupuesto='0', materia_id=2)
    assigned = action(client, new, 'publicar')
    assert assigned.status_code == 200
    data = assigned.json()['tarea']
    assert data['estado'] == 'asignada' and data['presupuesto'] == '0.00'
    assert data['estudiante_asignado']['id'] == 1
    assert [s['id'] for s in client.get('/estudiantes?materia=2', headers=headers('estudiante')).json()['items']] == [2]
    assert action(client, new, 'publicar').status_code == 409
    assert client.put(f'/tareas/{new}', headers=headers(), json={'titulo': 'Cambio'}).status_code == 409
    pending = draft(client)
    assert action(client, pending, 'publicar').json()['tarea']['estado'] == 'pendiente_asignacion'
    assert client.get('/estudiantes?materia=999', headers=headers()).status_code == 404
    assert client.get('/estudiantes', headers=headers()).status_code == 422


def test_full_lifecycle_permissions_and_history(api):
    client, _ = api
    tid = draft(client)
    assert action(client, tid, 'publicar', actor_id=2).status_code == 403
    assert action(client, tid, 'publicar').status_code == 200
    assert action(client, tid, 'iniciar').status_code == 403
    assert action(client, tid, 'iniciar', 'estudiante', 2).status_code == 403
    assert client.get(f'/tareas/{tid}', headers=headers('estudiante')).status_code == 200
    assert action(client, tid, 'enviar-revision', 'estudiante').status_code == 409
    assert action(client, tid, 'iniciar', 'estudiante').json()['tarea']['estado'] == 'en_desarrollo'
    assert action(client, tid, 'finalizar').status_code == 409
    assert action(client, tid, 'enviar-revision', 'estudiante').json()['tarea']['estado'] == 'en_revision'
    assert action(client, tid, 'iniciar', 'estudiante').status_code == 409
    assert action(client, tid, 'finalizar', 'estudiante').status_code == 403
    finished = action(client, tid, 'finalizar').json()['tarea']
    assert finished['estado'] == 'finalizada' and finished['estudiante_asignado']['id'] == 1
    assert client.get('/estudiantes?materia=1', headers=headers()).json()['total'] == 1
    for name in ['publicar', 'finalizar', 'cancelar']:
        assert action(client, tid, name).status_code == 409
    assert action(client, tid, 'iniciar', 'estudiante').status_code == 409


@pytest.mark.parametrize('state', ['borrador', 'pendiente', 'asignada', 'desarrollo', 'revision'])
def test_cancel_all_active_states(api, state):
    client, _ = api
    tid = draft(client, materia_id=3 if state == 'pendiente' else 1)
    if state != 'borrador':
        assert action(client, tid, 'publicar').status_code == 200
    if state in {'desarrollo', 'revision'}:
        action(client, tid, 'iniciar', 'estudiante')
    if state == 'revision':
        action(client, tid, 'enviar-revision', 'estudiante')
    result = action(client, tid, 'cancelar')
    assert result.status_code == 200
    assert result.json()['tarea']['estado'] == 'cancelada'
    if state in {'asignada', 'desarrollo', 'revision'}:
        assert result.json()['tarea']['estudiante_asignado']['id'] == 1
    assert action(client, tid, 'cancelar').status_code == 409
    assert client.get('/estudiantes?materia=1', headers=headers()).json()['total'] == 1


def test_release_does_not_reassign_pending(api):
    client, _ = api
    first, second = draft(client), draft(client)
    action(client, first, 'publicar')
    action(client, second, 'publicar')
    action(client, first, 'cancelar')
    assert client.get(f'/tareas/{second}', headers=headers()).json()['estado'] == 'pendiente_asignacion'


def test_comments_and_correction(api):
    client, _ = api
    tid = draft(client)
    url = f'/tareas/{tid}/comentarios'
    def comment(role='solicitante', aid=1, correction=False):
        return client.post(url, headers=headers(role, aid), json={'contenido': '  Revisar  ', 'requiere_correccion': correction})
    assert comment(correction=True).status_code == 409
    assert comment(aid=2).status_code == 403
    ordinary = comment()
    assert ordinary.status_code == 201 and ordinary.json()['estado'] == 'borrador'
    assert ordinary.json()['comentario']['contenido'] == 'Revisar'
    action(client, tid, 'publicar')
    action(client, tid, 'iniciar', 'estudiante')
    corrected = comment(correction=True)
    assert corrected.json()['estado'] == 'en_revision'
    assert comment('estudiante', correction=True).json()['estado'] == 'en_revision'
    assert client.get('/estudiantes?materia=1', headers=headers()).json()['total'] == 0
    detail = client.get(f'/tareas/{tid}', headers=headers()).json()
    assert len(detail['comentarios']) == 3 and detail['comentarios'][-1]['autor']['rol'] == 'estudiante'
    assert detail['comentarios'][0]['fecha'].endswith('Z')
    action(client, tid, 'finalizar')
    assert comment('estudiante').json()['estado'] == 'finalizada'
    assert comment(correction=True).status_code == 409
