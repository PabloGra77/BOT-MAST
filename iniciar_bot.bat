@echo off
cd /d "%~dp0"
echo Iniciando BOT...
echo Acceda a http://127.0.0.1:5000 en su navegador.
if not exist ".venv\Scripts\python.exe" (
	echo ERROR: No se encontró el entorno virtual. Ejecute primero INSTALAR_EN_PC_NUEVO.bat
	pause
	exit /b 1
)
REM Ejecutar desde la carpeta BOT360 para que los imports funcionen
pushd "%~dp0"
".venv\Scripts\python.exe" -m bot360_app.web.server
popd
pause
