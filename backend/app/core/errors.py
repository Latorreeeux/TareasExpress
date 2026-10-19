import logging
import sqlite3

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


class BusinessError(Exception):
    def __init__(self, status, code, message, *, fields=None, task_id=None, state=None, missing=None):
        self.status = status
        self.error = {"codigo": code, "mensaje": message, "campos": fields or []}
        self.body = {"error": self.error}
        if missing is not None:
            self.error["campos_faltantes"] = missing
        if task_id is not None:
            self.body.update(tarea_id=task_id, estado=state)
        super().__init__(message)


def register_errors(app):
    @app.exception_handler(BusinessError)
    async def business(_, exc):
        return JSONResponse(exc.body, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation(_, exc):
        fields = [{"campo": ".".join(str(v) for v in err["loc"]), "tipo": err["type"]} for err in exc.errors()]
        return JSONResponse({"error": {"codigo": "validacion", "mensaje": "Datos inválidos", "campos": fields}}, status_code=422)

    @app.exception_handler(HTTPException)
    async def http(_, exc):
        return JSONResponse({"error": {"codigo": "http_error", "mensaje": "Petición no permitida", "campos": []}}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unexpected(_, exc):
        locked = isinstance(exc, OperationalError) and (
            getattr(exc.orig, 'sqlite_errorcode', None) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
            or 'locked' in str(exc.orig).lower())
        if locked:
            return JSONResponse({"error": {"codigo": "base_ocupada", "mensaje": "Base ocupada temporalmente", "campos": []}}, status_code=503)
        logger.error("Fallo interno en operación", exc_info=exc)
        return JSONResponse({"error": {"codigo": "error_interno", "mensaje": "No se pudo completar la operación", "campos": []}}, status_code=500)
