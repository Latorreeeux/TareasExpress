# Datos y transacciones

Solicitantes y estudiantes tienen identidades separadas. La tabla de especialidades
relaciona estudiantes y materias. Cada tarea conserva su solicitante, materia,
archivos, comentarios y la asignación histórica al finalizar o cancelar.
Un comentario tiene exactamente un autor de uno de los dos roles.

El presupuesto se conserva como centavos enteros, nunca como float. Los estados
son siete valores cerrados. El índice único parcial sobre el estudiante impide
dos tareas en asignada, en_desarrollo o en_revision para una misma persona.

Cada unidad de trabajo usa su propia sesión y transacción. Las escrituras emiten
BEGIN IMMEDIATE antes de consultar negocio; las lecturas usan BEGIN. Se desactiva
el BEGIN implícito del driver. No se usa SELECT FOR UPDATE para bloquear SQLite.
Las conexiones activan foreign_keys, WAL y busy_timeout. SQLite acepta un escritor
por vez; el agotamiento del timeout se devuelve como 503, sin reintentos ocultos.
