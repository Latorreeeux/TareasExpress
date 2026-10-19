import os
import subprocess
import sys

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from conftest import headers


def test_fresh_cli_full_api_and_restart(tmp_path):
    db_path = tmp_path / 'fresh.db'
    uploads = tmp_path / 'uploads'
    env = {**os.environ, 'APP_ENV': 'local', 'DATABASE_URL': f'sqlite:///{db_path}', 'UPLOAD_DIR': str(uploads)}
    for args in [['init-db'], ['seed', '--file', 'examples/seed.json']]:
        completed = subprocess.run([sys.executable, '-m', 'app.cli', *args], env=env, capture_output=True, text=True)
        assert completed.returncode == 0, completed.stderr
    settings = Settings(_env_file=None, database_url=f'sqlite:///{db_path}', upload_dir=uploads)
    app = create_app(settings)
    with TestClient(app) as client:
        schema = client.get('/openapi.json').json()
        methods = {'get', 'post', 'put', 'patch', 'delete'}
        operations = [(path, method) for path, value in schema['paths'].items() for method in value if method in methods]
        assert len(operations) == 12
        for path, method in operations:
            assert {'X-Actor-Rol', 'X-Actor-Id'} <= {p['name'] for p in schema['paths'][path][method]['parameters']}
        assert client.get('/docs').status_code == 200
        created = client.post('/tareas', headers=headers(), json={'titulo': 'Inicial'})
        tid = created.json()['tarea']['id']
        data = {'titulo': 'Ejercicio', 'materia_id': 1, 'descripcion': 'Desarrollar', 'fecha_limite': '2026-12-31', 'presupuesto': '15.35'}
        assert client.put(f'/tareas/{tid}', headers=headers(), json=data).status_code == 200
        attachment = client.post(f'/tareas/{tid}/archivos', headers=headers(), files={'archivos': ('instrucciones.txt', b'Consigna', 'text/plain')})
        assert attachment.status_code == 201
        assert client.post(f'/tareas/{tid}/comentarios', headers=headers(), json={'contenido': 'Indicaciones'}).status_code == 201
        assert client.get('/tareas', headers=headers()).json()['total'] == 1
        assert client.get('/estudiantes?materia=1', headers=headers()).json()['total'] == 1
        assert client.put(f'/tareas/{tid}/publicar', headers=headers()).json()['tarea']['estado'] == 'asignada'
        assert client.put(f'/tareas/{tid}/iniciar', headers=headers('estudiante')).status_code == 200
        assert client.put(f'/tareas/{tid}/enviar-revision', headers=headers('estudiante')).status_code == 200
        assert client.put(f'/tareas/{tid}/finalizar', headers=headers()).status_code == 200
        second = client.post('/tareas', headers=headers(), json={}).json()['tarea']['id']
        assert client.put(f'/tareas/{second}/cancelar', headers=headers()).status_code == 200
    restarted = create_app(settings)
    with TestClient(restarted) as client:
        detail = client.get(f'/tareas/{tid}', headers=headers()).json()
        assert detail['estado'] == 'finalizada' and detail['presupuesto'] == '15.35'
        assert detail['estudiante_asignado']['id'] == 1
        assert detail['comentarios'][0]['contenido'] == 'Indicaciones'
        key = detail['archivos'][0]['ubicacion']
        assert (uploads / key).read_bytes() == b'Consigna'
        assert client.get('/tareas', headers=headers(actor_id=2)).json()['total'] == 0


def test_startup_does_not_create_database_or_seed(tmp_path):
    path = tmp_path / 'not-created.db'
    settings = Settings(_env_file=None, database_url=f'sqlite:///{path}', upload_dir=tmp_path / 'not-created-uploads')
    with TestClient(create_app(settings)) as client:
        assert client.get('/docs').status_code == 200
    assert not path.exists() and not settings.upload_dir.exists()


def test_large_file_within_default_limit(api):
    from conftest import draft
    client, app = api
    tid = draft(client)
    content = b'x' * (1024 * 1024 + 1)
    result = client.post(f'/tareas/{tid}/archivos', headers=headers(), files={'archivos': ('large.bin', content)})
    assert result.status_code == 201
    file = result.json()['archivos'][0]
    assert file['tamano_bytes'] == len(content)
    assert (app.state.settings.upload_dir / file['ubicacion']).read_bytes() == content
