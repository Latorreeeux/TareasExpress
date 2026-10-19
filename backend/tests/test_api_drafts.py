import pytest

from conftest import headers, draft


@pytest.mark.parametrize('identity,status', [
    ({}, 401), ({'X-Actor-Rol': 'solicitante'}, 401),
    (headers(actor_id=99), 401), (headers(role='admin'), 422),
    (headers(actor_id=0), 422), (headers(actor_id='abc'), 422),
    (headers(role='estudiante'), 403),
])
def test_identity(api, identity, status):
    client, _ = api
    response = client.get('/tareas', headers=identity)
    assert response.status_code == status
    assert set(response.json()['error']) == {'codigo', 'mensaje', 'campos'}


def test_create_edit_query_and_isolation(api):
    client, _ = api
    response = client.post('/tareas', headers=headers(), json={})
    assert response.status_code == 201
    item = response.json()['tarea']
    assert item['estado'] == 'borrador' and item['estudiante_asignado'] is None
    tid = item['id']
    edited = client.put(f'/tareas/{tid}', headers=headers(), json={'titulo': '  Nuevo  ', 'presupuesto': '0'}).json()['tarea']
    assert edited['titulo'] == 'Nuevo' and edited['presupuesto'] == '0.00'
    assert edited['creada_en'].endswith('Z')
    assert client.put(f'/tareas/{tid}', headers=headers(), json={}).json()['tarea']['titulo'] == 'Nuevo'
    assert client.put(f'/tareas/{tid}', headers=headers(), json={'titulo': None}).json()['tarea']['titulo'] is None
    assert client.get('/tareas', headers=headers(actor_id=2)).json() == {'items': [], 'total': 0}
    assert client.get(f'/tareas/{tid}', headers=headers(actor_id=2)).status_code == 403
    assert client.put(f'/tareas/{tid}', headers=headers(actor_id=2), json={'titulo': 'Ajeno'}).status_code == 403
    detail = client.get(f'/tareas/{tid}', headers=headers()).json()
    assert detail['archivos'] == [] and detail['comentarios'] == []
    assert client.get('/tareas', headers=headers()).json()['total'] == 1


def test_reference_and_validation_errors(api):
    client, _ = api
    assert client.get('/tareas/999', headers=headers()).status_code == 404
    assert client.post('/tareas', headers=headers(), json={'materia_id': 999}).status_code == 404
    response = client.post('/tareas', headers=headers(), json={'solicitante_id': 2, 'presupuesto': '-1'})
    assert response.status_code == 422 and len(response.json()['error']['campos']) == 2
    assert client.get('/tareas', headers=headers()).json()['total'] == 0


def test_openapi_headers(api):
    client, _ = api
    operation = client.get('/openapi.json').json()['paths']['/tareas']['get']
    assert {'X-Actor-Rol', 'X-Actor-Id'} <= {p['name'] for p in operation['parameters']}
