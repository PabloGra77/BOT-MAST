# Arquitectura de la aplicación de agenda Bot

La aplicación se compone de una API segura, una interfaz web y un bot automatizado que configura y genera agendas usando Selenium.

## Capas principales

- Presentación: rutas en `agenda_app/routes/ui.py` que sirven una página HTML con formulario y JavaScript para comunicarse con la API.
- API: rutas en `agenda_app/routes/agenda_api.py` que reciben solicitudes JSON, validan datos y crean jobs asíncronos.
- Dominio: modelos y servicios en `agenda_app/models.py` y `agenda_app/services/agenda_service.py` que encapsulan reglas de negocio.
- Infraestructura: integración con el bot Selenium en `agenda_app/bot/runner.py` y lectura de profesionales desde Excel en `agenda_app/bot/excel_lookup.py`.

## Seguridad

- Autenticación mediante API key en cabecera `X-API-Key`.
- Validación estricta de datos de entrada en `AgendaRequest`.
- Protección XSS al usar plantillas controladas y JSON para la comunicación entre front y API.
- Uso recomendado de HTTPS mediante un proxy inverso (Nginx, Apache o el propio hosting).

## Flujo de generación de agenda

1. El usuario completa el formulario web.
2. El navegador envía un `POST /api/agenda` con JSON y la API key.
3. El backend valida los datos y crea un job asíncrono.
4. Un hilo de fondo ejecuta `run_bot_job`, que:
   - Busca al profesional en el Excel.
   - Calcula horas de inicio y fin.
  - Genera un archivo temporal a partir de `config/config.json` con la configuración de agenda y generación.
   - Lanza `Bot` para configurar y generar la agenda.
5. El usuario consulta el estado del job con `GET /api/agenda/{job_id}` y ve mensajes de progreso.

## Endpoints de la API

- `POST /api/agenda`
  - Cabeceras: `Content-Type: application/json`, `X-API-Key: <clave>`
  - Cuerpo:
    - `sede` (string)
    - `cc` (string numérica)
    - `fecha` (string `DD/MM/YYYY` o `hoy`)
    - `hora_inicio` (string `HH:MM`)
    - `duracion_min` (entero)
    - `cantidad` (entero)
  - Respuestas:
    - `202 Accepted` con `{ "job_id": "<uuid>" }` si se acepta la solicitud.
    - `400 Bad Request` con `{ "error": "<detalles>" }` si hay errores de validación.
    - `401 Unauthorized` si falta o es incorrecta la API key.

- `GET /api/agenda/{job_id}`
  - Cabeceras: `X-API-Key: <clave>`
  - Respuestas:
    - `200 OK` con `{ "status": "...", "detail": "...", "created_at": "..." }`.
    - `404 Not Found` si el job no existe.

## Despliegue

### Servidor de aplicación

1. Instalar dependencias con `pip install -r config/requirements.txt`.
2. Definir variables de entorno:
   - `AGENDA_SECRET_KEY`
   - `AGENDA_API_KEY`
   - `AGENDA_LOG_PATH` (opcional)
3. Ejecutar la aplicación WSGI usando `bot360_app/web/wsgi.py` con un servidor como Gunicorn o Waitress.

## Estructura operativa

- `config/`: configuración principal y archivos de dependencias.
- `downloads/hc/`: salidas masivas de historias clínicas.
- `downloads/browser/`: descargas temporales controladas por Chrome/Selenium.
- `downloads/runtime/job_configs/`: configuraciones temporales por job.
- `logs/`: logs persistentes de la aplicación.
- `logs/runtime/`: artefactos de depuración y resúmenes de ejecución.
- `scripts/`: utilidades operativas y de diagnóstico.

### Integración con cPanel o front externo

- Servir un HTML estático que envíe solicitudes a la URL pública del backend.
- Configurar el atributo `action` del formulario o las llamadas `fetch` para apuntar al dominio del backend.
- Asegurar que el dominio use HTTPS y que el backend sea accesible desde la red donde se use la página.

## Pruebas

- Pruebas unitarias en `tests/test_agenda_service.py` y de integración de API en `tests/test_agenda_api.py`.
- Ejecutar con `python -m unittest discover`.
