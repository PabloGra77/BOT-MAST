# Changelog

## [1.0.4] - 2026-07-16

### Corrección crítica — soportes (PDF) en blanco
- **Causa raíz encontrada**: `_mover_a_subcarpeta` sí detectaba PDFs en blanco
  (peso insuficiente o sin texto extraíble vía `_validar_pdf_no_vacio`), pero
  la validación estaba marcada explícitamente como "informativa, NO
  bloqueante": solo se registraba una advertencia en el log y el PDF en
  blanco se renombraba y entregaba igual como si fuera un soporte válido.
  Esto afectaba a las descargas que llegaban por el flujo de descarga
  automática del navegador (a diferencia del flujo de descarga HTTP directa,
  que ya rechazaba y reintentaba PDFs en blanco desde la v1.0.1/1.0.2).
- **Cuarentena en vez de entrega silenciosa**: Ahora, cuando el PDF está en
  blanco/corrupto, se aísla en una subcarpeta `_REVISAR_BLANCO` dentro de la
  carpeta del servicio (nunca se sobreescribe ni se mezcla con soportes
  válidos) y `descargar_historia_clinica` devuelve un fallo explícito en vez
  de reportar éxito.
- **Reintento automático con sesión fresca**: `_es_resultado_transitorio_hc`
  (en `runner.py`) ahora reconoce "pdf en blanco" como resultado transitorio,
  por lo que el bot reintenta automáticamente la descarga (rotando
  credencial/navegador) en vez de dejar pasar el PDF en blanco o marcar la
  fila como fallo definitivo sin reintentar.
- La validación de servicio/fecha (que sí puede tener falsos positivos) se
  mantiene informativa y no bloqueante, tal como se definió previamente.

### Corrección de bug — NameError en verificación de actualizaciones
- `desktop_app.py`: las variables `except Exception as ex` se referenciaban
  dentro de un `lambda` diferido con `QTimer.singleShot`. Python borra esa
  variable al salir del bloque `except`, así que al ejecutarse el lambda
  ocurría un `NameError` y el mensaje de error real nunca se mostraba. Ahora
  el mensaje se captura en una variable normal antes de programar el lambda.

## [1.0.3] - 2026-06-16

### Correcciones de bugs — lógica NUMERO DE INGRESO
- **Extracción de ingreso ignora la cédula**: `_extraer_numero_ingreso_de_fila`
  ahora recibe la cédula del paciente y la excluye explícitamente de los
  candidatos, evitando que se confunda la cédula con el número de ingreso.
- **Extracción por contexto semántico**: Antes de usar heurística numérica,
  el extractor busca el número que aparece después de palabras clave como
  "INGRESO", "NRO. ING", etc. en el texto de la fila.
- **Exclusión de fechas en formato DDMMYYYY / YYYYMMDD**: Los valores de 8
  dígitos que son fechas válidas ya no se toman como número de ingreso.
- **Comparación normalizada de ingresos**: La verificación
  `ingreso_fila != ingreso_solicitado` ahora elimina ceros a la izquierda en
  ambos lados antes de comparar, evitando falsos negativos (ej: `"056789" vs "56789"`).
- **Mensaje de error correcto**: El mensaje cuando no se encuentra el ingreso
  ya no dice "en el rango de fechas" cuando la estrategia es RECIENTE/ANTIGUA.
- **`_obtener_numero_ingreso_paciente` — búsqueda case-insensitive**: La
  función ahora también busca la columna "NUMERO INGRESO" con variantes de
  mayúsculas, minúsculas, espacios extra y puntos, cubriendo los nombres que
  Excel puede generar al leer la plantilla.

---

## [1.0.2] - 2026-06-16

### Correcciones de bugs
- **Pestaña PDF bloqueada**: El bot ahora intenta la descarga HTTP de forma
  inmediata en cuanto detecta la pestaña del visor PDF, sin esperar 30 segundos
  inútiles. Timeout de detección de pestaña aumentado de 8s a 15s para servidores
  lentos.
- **`--disable-popup-blocking`**: Se agrega esta opción a Chrome/Edge para que
  la pestaña del PDF pueda abrirse libremente sin ser bloqueada por el navegador.
- **PDF en blanco desde descarga automática**: `_esperar_archivo_descargado`
  ahora exige que el archivo tenga al menos `PDF_MIN_BYTES` (5 KB) antes de
  considerarlo completado, evitando PDFs de cero bytes.
- **Espera en pestaña PDF aumentada**: La pausa post-`readyState=complete`
  subió de 2s a 5s para dar tiempo al servidor a generar el PDF completo.
- **`seleccionar_servicio` devuelve `None` en vez de `False`**: Faltaba
  `return False` al final del `try` cuando no había coincidencia exacta.
- **`_verificar_navegador_operativo_o_error` silenciaba la excepción correcta**:
  El `except` externo tragaba el mensaje específico; ahora cada condición tiene
  su propio bloque `try/except`.
- **Docstring mal ubicada en `descargar_historia_clinica`**: La cadena de
  documentación estaba después de código ejecutable; movida al inicio de la función.
- **`_reintento=2` en RANGO FECHAS deshabilitaba la recuperación del driver**:
  Cambiado a `_reintento=0` para que cada fila pueda reiniciar el navegador si cae.
- **`verify=False` en descarga HTTP** (seguridad): Cambiado a `verify=True`
  para validar el certificado SSL del servidor INPEC.
- **BOM UTF-8 en `bot_engine.py`**: El archivo se guardaba con BOM (EF BB BF),
  causando fallo en `ast.parse()` y herramientas de análisis estático.

---

## [1.0.1] - 2026-06-10

### Correcciones de bugs
- **Solo descarga ATENDIDA**: El filtro de estado ahora es ESTRICTO. Solo se
  descargan filas cuyo estado sea exactamente "ATENDIDA". Cualquier otro estado
  (POR ATENDER, NO ASISTIDA, CANCELADA, etc.) es descartado en todos los flujos
  (RECIENTE, ANTIGUA y RANGO FECHAS).
- **PDF en blanco**: El bot descargaba PDFs vacios porque actuaba demasiado
  rapido antes de que el servidor terminara de generar el documento.
- **Segunda pestana demasiado rapida**: `_detectar_ventana_nueva` ahora espera
  a que `document.readyState == 'complete'` + 2s extra antes de proceder.
- **Descarga HTTP sin validacion**: `_descargar_pdf_desde_contexto_actual`
  espera hasta 10s a que la URL sea PDF valido, valida tamano/contenido del PDF
  y reintenta hasta 3 veces (esperas 3s-6s-9s) si viene vacio.
- **Archivo con tamano cero**: `_esperar_archivo_descargado` verifica
  tamano > 0 bytes antes de dar el archivo por completado.
- **Timeout de descarga aumentado**: `HC_DESCARGA_TIMEOUT` subido de 20s a 30s.

---

## [1.0.0] - 2024-01-06

### Nuevo
- Implementacion inicial de aplicacion desktop con PyQt6
- Automatizacion Selenium para INPEC Salud 360
- Descarga de Historias Clinicas (HC) en PDF
- Generacion automatica de agendas
- Multi-navegador en paralelo (hasta 8)

### Cambios
- Migracion de interfaz WEB a desktop
- Reorganizacion de estructura del proyecto
