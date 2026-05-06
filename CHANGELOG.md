# Changelog

Todos los cambios notables a este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adherá a [Semantic Versioning](https://semver.org/lang/es/).

## [1.0.0] - 2024-01-06

### ✨ Added (Nuevo)
- Implementación inicial de aplicación desktop con PyQt6
- API REST completa con 6 endpoints
- Automatización Selenium para INPEC Salud 360
- Gestión de jobs asíncronos con ThreadPoolExecutor
- Descarga de Historias Clínicas (HC) en PDF
- Generación automática de agendas
- Rate limiting y seguridad en API
- Logging estructurado
- Documentación completa

### 🔧 Changed (Cambios)
- **BREAKING**: Migración de interfaz WEB a desktop
- Reorganización de estructura del proyecto para GitHub
- Movimiento de código a carpeta `src/`
- Mejora de manejo de errores
- Optimización de selectores XPath

### 🔐 Fixed (Reparado)
- Credenciales expuestas → Movidas a variables de entorno
- Carpetas duplicadas eliminadas (.venv, build)
- Archivos de log consolidados
- Imports incompletos en inpec_bot.py
- IE WebDriver deprecado → Reemplazado con Chrome/Edge

### 🗑️ Removed (Eliminado)
- Interfaz WEB (Flask port 5000)
- Carpeta build/ antigua
- Archivos de configuración inseguros
- Selectores genéricos y débiles

### 🚨 Security
- Implementación de .env para credenciales
- Creación de .env.example template
- API key validation robusta
- Rate limiting por IP

---

## [0.9.0] - 2023-12-20 (Versión anterior)

### Features
- Prototipo de bot Selenium
- API básica con Flask
- Gestión simple de agendas

---

## [Unreleased] - En desarrollo

### Planeado para 1.1.0
- [ ] Autenticación OAuth2
- [ ] Base de datos PostgreSQL
- [ ] Dashboard mejorado
- [ ] Exportación a múltiples formatos
- [ ] Notificaciones por email
- [ ] Sincronización en tiempo real

### Bajo consideración
- [ ] Soporte multi-usuario
- [ ] API GraphQL
- [ ] Aplicación móvil
- [ ] Integración con otros sistemas

---

## Convenciones de Versioning

### Major (X.0.0)
- Cambios que rompen compatibilidad
- Grandes refactorizaciones

### Minor (1.X.0)
- Nuevas características
- Mejoras sin romper compatibilidad

### Patch (1.0.X)
- Corrección de bugs
- Mejoras de seguridad

---

**Nota**: Las versiones anteriores a 1.0.0 fueron versiones de desarrollo sin soporte.

