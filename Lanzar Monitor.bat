@echo off
cd /d "%~dp0"
echo Iniciando Monitor de Ofertas...
python launcher_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocurrio un error al iniciar el programa.
    pause
)
