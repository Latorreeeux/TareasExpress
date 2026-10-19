import re
from tempfile import SpooledTemporaryFile

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    """Acota y almacena temporalmente el cuerpo antes de ejecutar el parser."""

    def __init__(self, app, limit):
        self.app = app
        self.limit = limit

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] not in {'POST', 'PUT'}:
            return await self.app(scope, receive, send)
        headers = dict(scope.get('headers', []))
        content_type = headers.get(b'content-type', b'').decode('latin-1').split(';')[0].strip().lower()
        if (scope['method'] == 'POST' and re.fullmatch(r'/tareas/[^/]+/archivos/?', scope['path'])
                and content_type != 'multipart/form-data'):
            return await self.reject(scope, receive, send, 415, 'tipo_invalido', 'Se requiere multipart/form-data')
        length = headers.get(b'content-length')
        if length:
            try:
                if int(length) < 0:
                    raise ValueError
                if int(length) > self.limit:
                    return await self.reject(scope, receive, send, 413, 'carga_excesiva', 'El cuerpo supera el límite permitido')
            except ValueError:
                return await self.reject(scope, receive, send, 422, 'validacion', 'Content-Length inválido')
        # El spool tiene límite de RAM y se elimina al cerrar, incluso tras errores.
        with SpooledTemporaryFile(max_size=1024 * 1024) as spool:
            size = 0
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                chunk = message.get('body', b'')
                size += len(chunk)
                if size > self.limit:
                    return await self.reject(scope, receive, send, 413, 'carga_excesiva', 'El cuerpo supera el límite permitido')
                await run_in_threadpool(spool.write, chunk)
                if not message.get('more_body', False):
                    break
            await run_in_threadpool(spool.seek, 0)
            remaining = size
            exhausted = False

            async def replay():
                nonlocal remaining, exhausted
                if exhausted:
                    return await receive()
                chunk = await run_in_threadpool(spool.read, 64 * 1024)
                remaining -= len(chunk)
                exhausted = remaining == 0
                return {'type': 'http.request', 'body': chunk, 'more_body': not exhausted}

            await self.app(scope, replay, send)

    @staticmethod
    async def reject(scope, receive, send, status, code, message):
        await JSONResponse({'error': {'codigo': code, 'mensaje': message, 'campos': []}}, status_code=status)(scope, receive, send)
