# BOT

Aplicación de **escritorio** (PyQt6) para automatizar la descarga de historias
clínicas y la gestión de agendas en el sistema INPEC (Salud360), usando Selenium.

![version](https://img.shields.io/badge/versión-1.0.0-2f81f7) ![python](https://img.shields.io/badge/python-3.9%2B-3776ab) ![plataforma](https://img.shields.io/badge/SO-Windows-555)

---

## ✨ Características

- Interfaz de escritorio profesional con pestañas (Dashboard, Credenciales, Navegadores, Historia Clínica).
- Descarga **masiva** de historias clínicas desde un Excel de pacientes.
- Estrategias por paciente: **Reciente**, **Antigua** y **Rango de fechas** (descarga todas las del rango).
- **Multi-navegador en paralelo** (hasta 8): cada uno con un usuario INPEC distinto.
- Refresco preventivo del navegador cada 20 registros para mantener la sesión estable.
- Renombrado del soporte por **número de factura** (con respaldo por número de ingreso).
- Botón **"Forzar Equipo"**: cierra apps pesadas para liberar RAM y dedicar el equipo al bot.
- **Auto-actualización**: detecta nuevas versiones y se actualiza con un clic.
- Huella mínima en disco: solo crea la carpeta de descargas y, ante un fallo, un `BOT_error.txt`.

---

## 🚀 Uso desde código fuente

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src/ui/desktop_app.py
```

En un PC nuevo sin Python puedes usar `INSTALAR_EN_PC_NUEVO.bat`.

## 🔨 Compilar el ejecutable

```bash
pip install pyinstaller pyinstaller-hooks-contrib
python build.py
# -> release/BOT_v1.0.0/BOT.exe  y  release/BOT_v1.0.0.zip
```

---

## 🔄 Actualizaciones

La app consulta los *Releases* de este repositorio. Para publicar una nueva versión:

1. Sube la versión en `__version__.py` (y `VERSION` en `src/ui/desktop_app.py`).
2. `python build.py` para generar `BOT.exe`.
3. Crea un *Release* en GitHub con tag `vX.Y.Z` y **adjunta `BOT.exe`** como asset.

Los usuarios verán el aviso de actualización al abrir la app y podrán actualizar con un clic.

---

## 📁 Estructura

```
src/
  ui/desktop_app.py        # aplicación de escritorio (punto de entrada)
  agenda_app/              # dominio + runner del bot
  bot_app/automation/      # motor Selenium (bot_engine.py)
config/                    # config.json (credenciales/sedes) — NO se versiona
build.py · bot.spec        # empaquetado (PyInstaller, onefile)
```

---

## 🔒 Seguridad

- `config/config.json` y `usuario/USUARIOS*.xlsx` están en `.gitignore` (credenciales / datos personales).
- **No publiques el `.exe` ni el ZIP en un repo público**: llevan las credenciales embebidas. Distribúyelos en privado.

## 📄 Licencia

MIT — ver [LICENSE](LICENSE).
