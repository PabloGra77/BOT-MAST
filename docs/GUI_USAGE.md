# 📖 Guía de Uso - GUI Desktop BOT360

## 🎯 Inicio

### 1. Ejecutar Aplicación

**Opción A: Desde código**
```bash
python -m src.ui.desktop_app
```

**Opción B: Desde ejecutable**
```bash
dist/BOT360/BOT360.exe
```

### 2. Pantalla Principal

```
┌─────────────────────────────────────────────┐
│ BOT360 - Panel de Control                   │
├─────────────────────────────────────────────┤
│ [Archivo] [Herramientas] [Ayuda]            │
├─────────────────────────────────────────────┤
│ [📅 Crear Agenda] [📥 Descargar HC] [...]   │
│ ┌─────────────────────────────────────────┐ │
│ │ Formulario / Tabla / Configuración      │ │
│ │                                         │ │
│ └─────────────────────────────────────────┘ │
├─────────────────────────────────────────────┤
│ [Log de Eventos]                            │
│ [01:30:45] ✅ Agenda completada            │
│ [01:30:50] 📥 HC descargada                │
├─────────────────────────────────────────────┤
│ Estado: Listo          Versión: v1.0.0     │
└─────────────────────────────────────────────┘
```

---

## 📋 Pestañas de la Interfaz

### Pestaña 1: 📅 Crear Agenda

Genera nueva agenda para un profesional.

**Campos:**
- **Sede**: Seleccionar de lista
- **Nombre Profesional**: Ej. Juan
- **Apellido**: Ej. García
- **Fecha Inicio**: YYYY-MM-DD (ej. 2024-01-15)
- **Fecha Fin**: YYYY-MM-DD (ej. 2024-02-15)
- **Servicios**: Ej. Psicología, Trabajo Social

**Botones:**
- 🟦 **Crear Agenda**: Ejecutar creación
- 🟦 **Limpiar Formulario**: Borrar campos

**Ejemplo:**
```
Sede: Bogotá
Nombre: Juan
Apellido: García
Fecha Inicio: 2024-01-15
Fecha Fin: 2024-02-15
Servicios: Psicología
↓
[Crear Agenda]
✅ Agenda creada exitosamente
```

---

### Pestaña 2: 📥 Descargar HC

Descarga Historias Clínicas en PDF.

**Campos:**
- **ID Paciente**: Número de identificación
- **Servicio**: Especialidad médica
- **Fecha Inicio**: Período de búsqueda
- **Fecha Fin**: Período de búsqueda

**Ejemplo:**
```
ID Paciente: 123456
Servicio: Psicología
Fecha Inicio: 2024-01-01
Fecha Fin: 2024-12-31
↓
[Descargar HC]
✅ HC descargada en: downloads/hc/
```

**Los archivos se guardan en:**
```
BOT360/downloads/hc/
├── HC_123456_Psicologia_2024-01-15.pdf
├── HC_123456_Psicologia_2024-02-10.pdf
└── ...
```

---

### Pestaña 3: 📊 Estado de Jobs

Monitorea trabajos en ejecución.

**Información mostrada:**
- Job ID: Identificador único
- Estado: En ejecución / Completado / Error
- Progreso: Barra de progreso
- Inicio: Hora de inicio
- Acciones: Pausar / Cancelar / Ver detalles

**Estados posibles:**
- 🔵 **En ejecución**: Job actualmente corriendo
- 🟢 **Completado**: Job terminó exitosamente
- 🔴 **Error**: Job falló
- 🟡 **Pausado**: Job en pausa

**Ejemplo de tabla:**
```
Job ID              Estado      Progreso   Inicio          Acciones
────────────────────────────────────────────────────────────────
job_123456          En ejecución ████░░░░░░ 14:30:25        [⏸] [◼]
job_789012          Completado   ██████████ 14:15:10        [▶] [✓]
job_345678          Error        ████░░░░░░ 13:45:00        [🔄] [✗]
```

---

### Pestaña 4: ⚙️ Configuración

Configurar parámetros de la aplicación.

**Opciones:**
- **API Key**: Clave de seguridad para API
- **Navegador**: Chrome / Edge / Firefox
- **Modo Headless**: Ejecutar sin ventana del navegador
- **Timeout**: Segundos máximo de espera

**Ejemplo:**
```
API Key: ••••••••••••••••••••••••• [Mostrar]
Navegador: [Chrome ▼]
☑ Modo Headless (sin ventana)
Timeout: 30 segundos

[Guardar Configuración]
✅ Configuración guardada
```

---

## 🎛️ Barra de Menú

### Archivo
- **Configuración**: Abrir diálogo de configuración
- **Salir**: Cerrar aplicación

### Herramientas
- **Ver Logs**: Abrir carpeta de logs (`logs/runtime/`)
- **Limpiar Descargas**: Borrar archivos en `downloads/`
- **Resetear Servidor**: Reiniciar servidor API

### Ayuda
- **Acerca de**: Información de la aplicación
- **Documentación**: Abrir README.md

---

## 📝 Log de Eventos

Panel inferior que muestra eventos en tiempo real.

**Formatos:**
```
[HH:MM:SS] ✅ Mensaje de éxito
[HH:MM:SS] ❌ Mensaje de error
[HH:MM:SS] ℹ️  Mensaje informativo
[HH:MM:SS] ⚠️  Advertencia
[HH:MM:SS] 🔄 Procesando...
```

**Ejemplo de log completo:**
```
[14:30:25] ✅ Aplicación iniciada
[14:30:45] 📅 Creando agenda para Juan García
[14:30:46] 🔄 Conectando a INPEC...
[14:31:02] ✅ Conectado
[14:31:15] 🔄 Generando agenda...
[14:31:45] ✅ Agenda completada
[14:32:00] 📥 Descargando historias clínicas...
[14:32:30] ✅ 5 archivos descargados
```

---

## ✨ Características Principales

### 1. Auto-actualización de Estado
- Se actualiza cada 5 segundos
- No requiere refrescar manualmente

### 2. Ejecución Asíncrona
- No bloquea la UI durante operaciones
- Puedes seguir usando mientras se ejecuta

### 3. Validación de Formularios
- Verifica campos requeridos
- Previene errores de entrada

### 4. Tema Oscuro
- Interfaz moderna y cómoda
- Colores azules (#0078d4) para contraste
- Fondo gris oscuro (#1e1e1e)

### 5. Responsive
- Se adapta a diferentes resoluciones
- Pestañas redimensionables

---

## 🔧 Solución de Problemas

### La GUI no inicia

**Error:** "ModuleNotFoundError: No module named 'PyQt6'"

**Solución:**
```bash
pip install PyQt6 PyQt6-Charts PyQt6-WebEngine
```

### No se conecta a INPEC

**Verificar:**
1. ✅ Credenciales en `.env` correctas
2. ✅ Conexión a internet activa
3. ✅ Sitio INPEC accesible
4. ✅ Navegador Chrome/Edge instalado

### El bot se detiene a mitad

**Revisar:**
1. Log de eventos en panel inferior
2. Archivos en `logs/runtime/` para detalles
3. Aumentar `Timeout` en Configuración

---

## 🎨 Personalización

### Cambiar Tema

Editar `src/ui/desktop_app.py`:
```python
def apply_theme(self):
    """Cambiar colores aquí"""
    self.setStyleSheet("""
        QMainWindow {
            background-color: #1e1e1e;  # Cambiar
            color: #ffffff;
        }
        ...
    """)
```

### Agregar Nueva Pestaña

```python
def create_mi_tab(self) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout()
    
    # Agregar widgets
    label = QLabel("Mi nueva pestaña")
    layout.addWidget(label)
    
    widget.setLayout(layout)
    return widget

# En create_ui():
tabs.addTab(self.create_mi_tab(), "Mi Tab")
```

---

## 📊 Monitoreo

### Registros de Ejecución

Los logs se guardan en:
```
BOT360/logs/runtime/
├── debug_visor.txt          # Debug detallado
├── resumen_ejecucion.txt    # Resumen de jobs
└── structure_scan.txt       # Estructura de INPEC
```

### Ver Logs desde GUI

Menú → Herramientas → Ver Logs

---

## ⌨️ Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl+Q` | Salir |
| `Ctrl+S` | Guardar configuración |
| `F1` | Ayuda |
| `Tab` | Siguiente campo |
| `Enter` | Ejecutar acción actual |

---

## 📱 API REST (Alternativa)

Si prefieres usar API REST en lugar de GUI:

```bash
# Iniciar servidor
python -m src.bot360_app.web.server

# Crear agenda
curl -X POST http://localhost:5000/api/agenda \
  -H "Authorization: Bearer $AGENDA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

---

## ✅ Checklist de Inicio

- [ ] Instalar BOT360 correctamente
- [ ] Copiar `.env.example` a `.env`
- [ ] Completar credenciales INPEC en `.env`
- [ ] Instalar Chrome o Edge
- [ ] Ejecutar primera prueba
- [ ] Revisar logs
- [ ] Programar tareas automáticas

---

**Versión:** 1.0.0
**Última actualización:** 2024-01-06
**Soporte:** https://github.com/tu-usuario/bot360/issues

