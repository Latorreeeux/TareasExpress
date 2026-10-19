from decimal import Decimal

from app.models.entities import ETIQUETAS
from app.schemas.contracts import ArchivoOut, ComentarioOut, TareaDetalle, TareaResumen


def archivo_out(file):
    return ArchivoOut(id=file.id, nombre=file.nombre_original, tipo=file.tipo, ubicacion=file.clave, tamano_bytes=file.tamano_bytes)


def comentario_out(comment):
    student = comment.autor_estudiante_id is not None
    person = comment.estudiante if student else comment.solicitante
    return ComentarioOut(id=comment.id, contenido=comment.contenido, fecha=comment.creada_en,
                         requiere_correccion=comment.requiere_correccion,
                         autor={'rol': 'estudiante' if student else 'solicitante', 'id': person.id, 'nombre': person.nombre})


def tarea_out(task, *, detail=True):
    values = dict(id=task.id, titulo=task.titulo, descripcion=task.descripcion, fecha_limite=task.fecha_limite,
                  presupuesto=Decimal(task.presupuesto_centavos) / 100 if task.presupuesto_centavos is not None else None,
                  estado=task.estado, estado_descripcion=ETIQUETAS[task.estado], solicitante=task.solicitante,
                  materia=task.materia, estudiante_asignado=task.estudiante, creada_en=task.creada_en,
                  actualizada_en=task.actualizada_en)
    if detail:
        return TareaDetalle(**values, archivos=[archivo_out(f) for f in task.archivos],
                            comentarios=[comentario_out(c) for c in task.comentarios])
    return TareaResumen(**values)
