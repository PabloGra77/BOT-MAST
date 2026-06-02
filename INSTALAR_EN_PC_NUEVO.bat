@echo off
setlocal EnableDelayedExpansion
title ASISTENTE DE INSTALACION - BOT
color 1F

echo ===========================================================================
echo       ASISTENTE DE INSTALACION PASO A PASO
echo ===========================================================================
echo.
echo [IMPORTANTE]
echo Asegurese de haber EXTRAIDO todos los archivos del ZIP antes de ejecutar esto.
echo Si esta ejecutando esto dentro del ZIP, cierre y extraiga primero.
echo.
echo Presione una tecla para comenzar el diagnostico...
pause

REM 1. LIMPIEZA SEGURA
echo.
echo [1/4] Preparando entorno...
if exist ".venv" (
    echo     - Eliminando configuracion anterior...
    rmdir /s /q ".venv" >nul 2>&1
)

REM 2. DETECCION DE PYTHON
echo.
echo [2/4] Buscando Python instalado...
set "PYTHON_CMD="

python --version >nul 2>&1
if !errorlevel! equ 0 set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
    py --version >nul 2>&1
    if !errorlevel! equ 0 set "PYTHON_CMD=py"
)

if not defined PYTHON_CMD (
    color 4F
    echo.
    echo [X] NO SE DETECTO PYTHON EN ESTE EQUIPO.
    echo.
    echo ---------------------------------------------------------------------
    echo   SOLUCION NECESARIA:
    echo ---------------------------------------------------------------------
    echo   1. Se abrira automaticamente la web de descarga de Python.
    echo   2. Descargue e instale la version mas reciente.
    echo   3. IMPORTANTE: Al instalar, marque la casilla "Add Python to PATH".
    echo   4. Una vez instalado, vuelva a esta ventana y presione cualquier tecla.
    echo ---------------------------------------------------------------------
    echo.
    echo Presione una tecla para abrir la web de descarga...
    pause
    start https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe
    
    echo.
    echo [ESPERANDO INSTALACION...]
    echo Instale Python y luego presione una tecla aqui para reintentar...
    pause
    
    REM Reintento
    python --version >nul 2>&1
    if !errorlevel! equ 0 set "PYTHON_CMD=python"
    
    if not defined PYTHON_CMD (
        py --version >nul 2>&1
        if !errorlevel! equ 0 set "PYTHON_CMD=py"
    )
    
    if not defined PYTHON_CMD (
        echo.
        echo [ERROR] Sigue sin detectarse Python.
        echo Intente reiniciar el PC o ejecutar este archivo como Administrador.
        pause
        exit /b 1
    )
)

echo [OK] Python encontrado: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

REM 3. CREAR ENTORNO
echo [3/4] Creando entorno virtual (esto puede tardar un poco)...
%PYTHON_CMD% -m venv .venv
if !errorlevel! neq 0 (
    color 4F
    echo [ERROR] No se pudo crear el entorno virtual.
    echo Asegurese de tener permisos en esta carpeta.
    pause
    exit /b 1
)

REM 4. INSTALAR
echo.
echo [4/4] Instalando librerias del Bot...
echo Por favor espere, esto puede tardar unos minutos...

echo    - Creando lista de requisitos compatible...
(
    echo selenium
    echo webdriver-manager
    echo pandas
    echo openpyxl
    echo requests
    echo pymupdf
    echo urllib3
    echo PyQt6
    echo psutil
    echo python-dotenv
) > requirements_compatible.txt

echo    - Actualizando herramientas de instalacion...
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel >nul 2>&1

set "MAX_RETRIES=3"
set "TRY=1"

:INSTALL_RETRY
echo    - Instalando librerias (intento !TRY! de !MAX_RETRIES!)...
if not exist "config" mkdir "config"
move /Y requirements_compatible.txt config\requirements_compatible.txt >nul 2>&1
.venv\Scripts\python.exe -m pip install -r config\requirements_compatible.txt --no-cache-dir

if !errorlevel! equ 0 goto INSTALL_OK

if !TRY! geq !MAX_RETRIES! goto INSTALL_FAIL

echo.
echo [AVISO] Fallo la instalacion en el intento !TRY!.
echo        Posible archivo bloqueado por OneDrive/antivirus/otro proceso Python.
echo        Se intentara recuperacion automatica...

REM Cerrar procesos Python que puedan bloquear archivos de la venv
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1

REM Limpiar posible bloqueo puntual de PyMuPDF
if exist ".venv\Lib\site-packages\pymupdf" (
    rmdir /s /q ".venv\Lib\site-packages\pymupdf" >nul 2>&1
)
if exist ".venv\Lib\site-packages\pymupdf*" (
    del /f /q ".venv\Lib\site-packages\pymupdf*" >nul 2>&1
)

timeout /t 2 /nobreak >nul
set /a TRY+=1
goto INSTALL_RETRY

:INSTALL_FAIL
color 4F
echo.
echo [ERROR CRITICO] Fallo la instalacion de librerias tras !MAX_RETRIES! intentos.
echo.
echo Posible causa: acceso denegado por archivo bloqueado en .venv (ej: pymupdf).
echo.
echo Recomendado:
echo   1) Cerrar todo Python/VSCode.
echo   2) Pausar OneDrive temporalmente.
echo   3) Ejecutar este instalador como Administrador.
echo.
echo Detalle del error:
echo Revise el texto rojo arriba.
pause
exit /b 1

:INSTALL_OK

echo.
echo ===========================================================================
echo                 INSTALACION EXITOSA
echo ===========================================================================
echo.
echo Iniciando la aplicacion de escritorio BOT...
echo Puede cerrar esta ventana cuando termine de usar el Bot.
echo.

.venv\Scripts\python.exe "%~dp0src\ui\desktop_app.py"

if !errorlevel! neq 0 (
    echo.
    echo [AVISO] El Bot se cerro. Si fue un error, tome captura de pantalla.
    pause
)
pause
