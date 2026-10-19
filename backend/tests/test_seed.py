import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.cli import SeedData, seed, main
from app.core.config import Settings
from app.db.database import Database
from app.models.entities import Estudiante, Materia, Tarea


def test_seed_idempotent_and_atomic(tmp_path):
    db = Database(Settings(_env_file=None, database_url=f'sqlite:///{tmp_path / "seed.db"}', upload_dir=tmp_path / 'uploads'))
    try:
        db.initialize()
        data = SeedData.model_validate_json(Path('examples/seed.json').read_bytes())
        seed(db, data)
        with db.uow(write=True) as s:
            s.get(Estudiante, 1).disponible = False
            s.add(Tarea(solicitante_id=1))
        seed(db, data)
        with db.uow() as s:
            assert not s.get(Estudiante, 1).disponible
            assert s.scalar(select(func.count()).select_from(Tarea)) == 1
        broken = data.model_dump()
        broken['materias'].append({'id': 4, 'nombre': 'Nueva'})
        broken['estudiantes'][0]['nombre'] = 'Conflicto'
        with pytest.raises(ValueError):
            seed(db, SeedData.model_validate(broken))
        with db.uow() as s:
            assert s.get(Materia, 4) is None
        duplicate = data.model_dump()
        duplicate['materias'] = [{'id': 50, 'nombre': 'Programación'}]
        duplicate['estudiantes'] = []
        with pytest.raises(ValueError):
            seed(db, SeedData.model_validate(duplicate))
    finally:
        db.dispose()


def test_bad_seed_references():
    data = json.loads(Path('examples/seed.json').read_text(encoding='utf-8'))
    data['estudiantes'][0]['materia_ids'] = [99]
    with pytest.raises(ValueError):
        SeedData.model_validate(data)


def test_cli(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{tmp_path / "cli.db"}')
    monkeypatch.setenv('UPLOAD_DIR', str(tmp_path / 'uploads'))
    assert main(['init-db']) == 0
    assert main(['seed', '--file', 'examples/seed.json']) == 0
    assert main(['seed', '--file', 'examples/seed.json']) == 0
    assert main(['seed', '--file', str(tmp_path / 'missing.json')]) == 1
