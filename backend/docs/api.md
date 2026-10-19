# Contrato HTTP

Los cuerpos JSON usan nombres en español y rechazan campos extra. En borrador
los campos titulo, materia_id, fecha_limite, descripcion y presupuesto pueden
faltar o ser null. PUT solo cambia los campos presentes; null borra un dato.
Título: 1-200 caracteres; descripción y comentario: 1-5000, tras quitar espacios.
Fecha límite: YYYY-MM-DD. Presupuesto: decimal no negativo, máximo 9999999999.99
y dos decimales. Se devuelve como cadena exacta con dos decimales.

Cada mutación de tarea devuelve mensaje y tarea con su id y estado.
Las consultas de listas devuelven items y total. Los errores siguen:

```json
{"error":{"codigo":"validacion","mensaje":"Datos inválidos","campos":[]}}
```

401: identidad ausente/desconocida; 403: actor sin permiso; 404: recurso inexistente;
409: transición inválida; 413: carga excesiva; 415: carga sin multipart;
422: datos inválidos; 503: SQLite ocupado; 500: fallo interno sin detalles públicos.

Cabeceras: X-Actor-Rol (solicitante o estudiante) y X-Actor-Id (entero positivo).
El ID debe existir en la tabla del rol. GET /tareas solo devuelve tareas propias
del solicitante; GET /tareas/{id} solo está permitido a sus participantes.
POST /tareas crea un borrador propio y PUT /tareas/{id} lo edita exclusivamente
mientras esté en Borrador. La identidad y el estado nunca vienen del cuerpo.

## Publicación y proceso

PUT /tareas/{id}/publicar exige los cinco datos obligatorios; cero es presupuesto
válido. Selecciona al primer estudiante disponible por ID con especialidad en la
materia. Si no hay candidato, confirma pendiente_asignacion. GET /estudiantes
requiere query materia y solo consulta candidatos: no asigna.

| Acción PUT | Desde | Hasta | Actor |
| --- | --- | --- | --- |
| iniciar | asignada | en_desarrollo | estudiante asignado |
| enviar-revision | en_desarrollo | en_revision | estudiante asignado |
| finalizar | en_revision | finalizada | solicitante propietario |
| cancelar | cualquier no terminal | cancelada | solicitante propietario |

Finalizar/cancelar libera al estudiante y conserva el historial. No reasigna tareas
pendientes. Las demás transiciones se rechazan con 409, incluido reiniciar desde
revisión. No existe carga de entregables del estudiante en esta versión.

POST /tareas/{id}/comentarios recibe contenido y requiere_correccion (false por
defecto). Solo comentan participantes. Un comentario ordinario no cambia el estado,
incluso terminal. Una corrección se acepta en en_desarrollo o en_revision y deja
en_revision. Estado y comentario se guardan en la misma transacción.

## Adjuntos

POST /tareas/{id}/archivos recibe multipart con el campo repetido `archivos`.
Solo el propietario carga en Borrador. Máximo 10 archivos y 10 MiB por archivo,
configurables. Antes del parser se aplica el límite global de 101 MiB, incluso
sin Content-Length. El contenido se conserva opaco, sin ejecutar ni abrir.

Respuesta: mensaje, tarea_id, estado y archivos (id, nombre, tipo, ubicacion,
tamano_bytes). Las ubicaciones son claves opacas relativas, sin rutas públicas.
No hay endpoint de descarga ni directorio estático. Un fallo del conjunto revierte
metadatos y limpia los archivos propios de esa petición. Tras una caída abrupta
pueden quedar archivos huérfanos: detener la API e inspeccionar las claves no
referenciadas por `archivos.clave` antes de retirarlos. Respaldar DB y uploads juntos.
