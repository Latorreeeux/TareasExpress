# Tareas Express Backend

API de desarrollo local con Python 3.12+, FastAPI, SQLite y SQLAlchemy.
Las cabeceras declaran una identidad de pruebas; no autentican personas.

Ejecuta los comandos de esta guía desde la carpeta `backend/`.

## Instalación en PowerShell

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Para reproducir las versiones comprobadas, instala `requirements.lock` en un
entorno nuevo y después el proyecto editable:

```powershell
./.venv/Scripts/python.exe -m pip install -r requirements.lock
./.venv/Scripts/python.exe -m pip install --no-deps -e .
```

La configuración solo acepta `APP_ENV=local`, SQLite en archivo y orígenes
CORS locales explícitos. Por defecto no se habilita CORS.
Los límites de carga son 10 MiB por archivo, 10 archivos por petición y
101 MiB por cuerpo multipart, incluido su margen de metadatos.

Las peticiones incluyen `X-Actor-Rol: solicitante` (o `estudiante`) y
`X-Actor-Id: 1` según el actor del seed. La identidad declarada no es verificable
y esta aplicación no debe exponerse públicamente. Swagger está en `/docs`.

## Arquitectura

- Presentación: `app/api` y `app/schemas`.
- Negocio y permisos: `app/services` y `app/core`.
- Datos: `app/models`, `app/repositories` y `app/db`.

Cada unidad de trabajo tiene su sesión. Los repositorios no hacen commit.
Los datos y las herramientas de especificación son locales y están excluidos de Git.

## Base y datos de ejemplo

```powershell
./.venv/Scripts/python.exe -m app.cli init-db
./.venv/Scripts/python.exe -m app.cli seed --file examples/seed.json
```

La API no crea tablas ni carga datos al arrancar. El seed es explícito, transaccional
e idempotente con datos idénticos; rechaza conflictos sin sobrescribir información.
No cambia la disponibilidad de estudiantes existentes ni las tareas.
`create_all` inicializa el esquema; no migra futuras versiones con datos existentes.
El modelo y las transacciones se describen en [docs/datos.md](docs/datos.md).

Ejecución local (después de inicializar la base):

```powershell
./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Uso de la API

```powershell
$taskHeaders = @{ 'X-Actor-Rol' = 'solicitante'; 'X-Actor-Id' = '1' }
$taskBody = @{ titulo='Ejercicio'; materia_id=1; fecha_limite='2026-12-31'; descripcion='Resolver'; presupuesto='100.25' } | ConvertTo-Json
$createdTask = Invoke-RestMethod http://127.0.0.1:8000/tareas -Method Post -Headers $taskHeaders -ContentType 'application/json' -Body $taskBody
$taskId = $createdTask.tarea.id
Invoke-RestMethod "http://127.0.0.1:8000/tareas/$taskId/publicar" -Method Put -Headers $taskHeaders
```

Los doce contratos, estados, errores y adjuntos están en [docs/api.md](docs/api.md)
y en Swagger, [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
La finalización requiere aceptación del solicitante desde revisión; cancelar o
finalizar libera al estudiante. No hay reintento de asignaciones pendientes ni
retorno desde revisión a desarrollo en este alcance.

## Comprobaciones

```powershell
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe -m pip check
```

Las pruebas usan bases y archivos temporales: cubren permisos, los doce endpoints,
precisión del presupuesto, persistencia, publicación concurrente y rollback de
fallos reales de commit y almacenamiento. No modifican los datos locales.

Detén la API para respaldar SQLite y uploads juntos. La carga compensa fallos de
la petición, pero una caída abrupta puede dejar archivos huérfanos; el procedimiento
de inspección está en la documentación de adjuntos. No se incluyen pagos,
notificaciones, frontend ni despliegue.
