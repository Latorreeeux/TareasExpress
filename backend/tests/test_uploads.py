from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from starlette.testclient import TestClient

from app.core.body_limit import BodyLimitMiddleware
from app.services.uploads import FileStorage, safe_path
from conftest import headers, draft
from test_lifecycle import action


def send(client, tid, files=None, **kwargs):
    return client.post(f'/tareas/{tid}/archivos', headers=headers(), files=files or [('archivos', ('test.txt', b'hola', 'text/plain'))], **kwargs)


def test_upload_and_detail(api):
    client, app = api
    tid = draft(client)
    result = send(client, tid, [('archivos', ('../../evil.txt', b'abc', 'text/plain')),
                              ('archivos', ('C:\\temp\\otro.pdf', b'%PDF', 'application/pdf'))])
    assert result.status_code == 201, result.text
    files = result.json()['archivos']
    assert [f['nombre'] for f in files] == ['evil.txt', 'otro.pdf']
    for f in files:
        assert '/' not in f['ubicacion'] and '\\' not in f['ubicacion']
        assert (app.state.settings.upload_dir / f['ubicacion']).is_file()
    detail = client.get(f'/tareas/{tid}', headers=headers()).json()
    assert detail['archivos'] == files
    assert not list((app.state.settings.upload_dir / '.staging').iterdir())
    action(client, tid, 'publicar')
    assert send(client, tid).status_code == 409
    assert client.post(f'/tareas/{tid}/archivos', headers=headers(), json={}).status_code == 415


def test_upload_limits_permissions_and_cleanup(api):
    client, app = api
    tid = draft(client)
    app.state.settings.max_upload_bytes = 3
    result = send(client, tid, [('archivos', ('one.txt', b'ok', 'text/plain')), ('archivos', ('two.txt', b'large', 'text/plain'))])
    assert result.status_code == 413
    assert client.get(f'/tareas/{tid}', headers=headers()).json()['archivos'] == []
    assert not [p for p in app.state.settings.upload_dir.rglob('*') if p.is_file()]
    app.state.settings.max_files_per_request = 1
    assert send(client, tid, [('archivos', ('1', b'a')), ('archivos', ('2', b'b'))]).status_code == 422
    assert client.post(f'/tareas/{tid}/archivos', headers=headers(actor_id=2), files={'archivos': ('x', b'a')}).status_code == 403
    assert client.post(f'/tareas/{tid}/archivos', headers=headers(), data={'archivos': 'not-file'}).status_code == 415


@pytest.mark.parametrize('with_length', [True, False])
def test_body_limit_before_parser(with_length):
    reached = []
    async def downstream(scope, receive, send):
        reached.append(True)
    limited = BodyLimitMiddleware(downstream, limit=32)
    client = TestClient(limited)
    try:
        extra = {'Content-Length': '64'} if with_length else {}
        # Un cuerpo por iterador evita que HTTPX calcule Content-Length.
        response = client.put('/tareas/1', headers=extra, content=iter([b'x' * 16] * 4))
    finally:
        client.close()
    assert response.status_code == 413 and not reached


def test_storage_path_escape(api, tmp_path):
    _, app = api
    with pytest.raises(OSError):
        safe_path(app.state.settings.upload_dir.resolve(), '..', 'outside')


def test_publication_during_staging(api, monkeypatch):
    client, app = api
    tid = draft(client)
    staged, release = Event(), Event()
    original = FileStorage.stage
    def delayed(self, files):
        result = original(self, files)
        staged.set()
        assert release.wait(5)
        return result
    monkeypatch.setattr(FileStorage, 'stage', delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(send, client, tid)
        assert staged.wait(5)
        try:
            assert action(client, tid, 'publicar').status_code == 200
        finally:
            release.set()
        assert pending.result(5).status_code == 409
    assert client.get(f'/tareas/{tid}', headers=headers()).json()['archivos'] == []
    assert not [p for p in app.state.settings.upload_dir.rglob('*') if p.is_file()]
