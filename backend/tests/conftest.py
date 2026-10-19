from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.cli import SeedData, seed
from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def api(tmp_path):
    settings = Settings(_env_file=None, database_url=f'sqlite:///{tmp_path / "api.db"}', upload_dir=tmp_path / 'uploads')
    app = create_app(settings)
    app.state.db.initialize()
    seed(app.state.db, SeedData.model_validate_json(Path('examples/seed.json').read_bytes()))
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, app


def headers(role='solicitante', actor_id=1):
    return {'X-Actor-Rol': role, 'X-Actor-Id': str(actor_id)}


def draft(client, **overrides):
    data = {'titulo': 'Tarea', 'materia_id': 1, 'descripcion': 'Resolver ejercicio',
            'fecha_limite': '2026-12-31', 'presupuesto': '100.25'}
    data.update(overrides)
    response = client.post('/tareas', headers=headers(), json=data)
    assert response.status_code == 201, response.text
    return response.json()['tarea']['id']
