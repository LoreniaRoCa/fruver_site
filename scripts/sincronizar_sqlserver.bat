@echo off
rem Sube la informacion de SQL Server a Supabase (manage.py subirsqlserver).
rem Uso:  scripts\sincronizar_sqlserver.bat 1   (1 = Inventario, 2 = Detalle de Ventas)
rem Lo ejecuta el Programador de tareas de Windows cada hora.

setlocal
set PROCESO=%~1
if "%PROCESO%"=="" set PROCESO=1

rem Carpeta del proyecto (la de arriba de scripts\)
cd /d "%~dp0.."
if not exist logs mkdir logs

rem La salida del comando tiene emojis: sin UTF-8 Python falla al escribirla en el log
set PYTHONUTF8=1

echo ===== %date% %time% proceso %PROCESO% ===== >> "logs\sincronizacion_%PROCESO%.log"
"venv\Scripts\python.exe" manage.py subirsqlserver --tabla %PROCESO% >> "logs\sincronizacion_%PROCESO%.log" 2>&1
set RESULTADO=%ERRORLEVEL%
echo ===== fin, codigo %RESULTADO% ===== >> "logs\sincronizacion_%PROCESO%.log"

exit /b %RESULTADO%
