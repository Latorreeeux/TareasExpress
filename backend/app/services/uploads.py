import logging
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.core.actors import require_owner
from app.core.errors import BusinessError
from app.models.entities import Archivo, Estado
from app.repositories.tasks import get_task
from app.schemas.contracts import ArchivosResult
from app.schemas.serialization import archivo_out
from app.services.tasks import require_state

logger = logging.getLogger(__name__)


@dataclass
class StagedFile:
    path: Path
    key: str
    name: str
    kind: str
    size: int


def safe_path(root: Path, *parts: str) -> Path:
    path = root.joinpath(*parts).resolve()
    if not path.is_relative_to(root):
        raise OSError('Destino fuera de la raíz de archivos')
    return path


def clean_name(name):
    name = (name or 'archivo').replace('\\', '/').rsplit('/', 1)[-1]
    name = ''.join(c for c in name if not unicodedata.category(c).startswith('C')).strip()[:255]
    return name if name not in {'', '.', '..'} else 'archivo'


class FileStorage:
    def __init__(self, settings):
        self.settings = settings
        self.root = settings.upload_dir.resolve()

    def stage(self, files):
        staged = []
        try:
            directory = safe_path(self.root, '.staging')
            directory.mkdir(parents=True, exist_ok=True)
            for upload in files:
                key = uuid4().hex
                path = safe_path(self.root, '.staging', key)
                item = StagedFile(path, key, clean_name(upload.filename), (upload.content_type or 'application/octet-stream')[:255], 0)
                staged.append(item)
                with path.open('xb') as destination:
                    while chunk := upload.file.read(64 * 1024):
                        item.size += len(chunk)
                        if item.size > self.settings.max_upload_bytes:
                            raise BusinessError(413, 'archivo_excesivo', 'Un archivo supera el límite permitido')
                        destination.write(chunk)
            return staged
        except BaseException:
            self.cleanup([f.path for f in staged])
            raise

    def move(self, item):
        target = safe_path(self.root, item.key)
        item.path.replace(target)
        return target

    def cleanup(self, paths):
        for path in paths:
            try:
                checked = safe_path(self.root, str(path.relative_to(self.root)))
                checked.unlink(missing_ok=True)
            except OSError:
                logger.exception('No se pudo limpiar un archivo local')


class UploadService:
    def __init__(self, db, storage):
        self.db = db
        self.storage = storage

    def upload(self, actor, task_id, files):
        if not 1 <= len(files) <= self.storage.settings.max_files_per_request:
            raise BusinessError(422, 'cantidad_archivos', 'Cantidad de archivos no permitida')
        with self.db.uow() as session:
            task = get_task(session, task_id)
            require_owner(task, actor)
            require_state(task, Estado.BORRADOR)
        staged = self.storage.stage(files)
        moved = []
        try:
            with self.db.uow(write=True) as session:
                task = get_task(session, task_id)
                require_owner(task, actor)
                require_state(task, Estado.BORRADOR)
                records = []
                for item in staged:
                    # Registrar destino antes del movimiento para compensar fallos posteriores.
                    target = safe_path(self.storage.root, item.key)
                    moved.append(target)
                    self.storage.move(item)
                    record = Archivo(tarea_id=task.id, nombre_original=item.name, tipo=item.kind,
                                     clave=item.key, tamano_bytes=item.size)
                    records.append(record)
                    session.add(record)
                session.flush()
                response = ArchivosResult(mensaje='Archivos adjuntados', tarea_id=task.id, estado=task.estado,
                                          archivos=[archivo_out(r) for r in records])
            return response
        except BaseException:
            self.storage.cleanup(moved)
            raise
        finally:
            self.storage.cleanup([f.path for f in staged])
