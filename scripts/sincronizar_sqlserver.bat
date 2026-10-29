@echo off
rem Sube la informacion de SQL Server a Supabase (sincronizar_sqlserver.py, sin Django).
rem Uso:  scripts\sincronizar_sqlserver.bat 1   (1 = Inventario, 2 = Detalle de Ventas)
rem Lo ejecuta el Programador de tareas de Windows cada hora.

setlocal
set PROCESO=%~1
if "%PROCESO%"=="" set PROCESO=1

rem Carpeta del proyecto (la de arriba de scripts\)
cd /d "%~dp0.."
if not exist logs mkdir logs

rem Salida en UTF-8 para que los acentos se escriban bien en el log
set PYTHONUTF8=1

echo ===== %date% %time% proceso %PROCESO% ===== >> "logs\sincronizacion_%PROCESO%.log"
"venv\Scripts\python.exe" sincronizar_sqlserver.py %PROCESO% >> "logs\sincronizacion_%PROCESO%.log" 2>&1
set RESULTADO=%ERRORLEVEL%
echo ===== fin, codigo %RESULTADO% ===== >> "logs\sincronizacion_%PROCESO%.log"

exit /b %RESULTADO%
