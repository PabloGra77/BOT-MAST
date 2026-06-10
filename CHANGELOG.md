# Changelog

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
