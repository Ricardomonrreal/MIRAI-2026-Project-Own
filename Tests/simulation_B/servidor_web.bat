@echo off
rem Sesion AURA en el navegador (MIRAI 2026) - doble clic para usarla.
rem Abre sesion_aura_web.py en una consola minimizada y luego http://localhost:8000.
rem La consola es necesaria: Detener manda Ctrl+Break al pipeline a traves de ella.
rem Para apagar todo: cerrar esa ventana o Ctrl+C en ella (los procesos se cierran sin reporte).
rem Si el servidor ya estaba encendido, solo abre la pagina.
rem Ruta absoluta: el .bat (o una copia) funciona desde cualquier carpeta, p. ej. el escritorio.
rem Si se mueve el proyecto, actualizar SIM_B.
setlocal
set "SIM_B=C:\Users\ricar\Documents\Ucaribe\MIRAI 2026\Project\Tests\simulation_B"
cd /d "%SIM_B%"
set PYTHONIOENCODING=utf-8
set URL=http://localhost:8000

curl -s -o nul %URL%/api/estado && goto abrir

start "Servidor sesion AURA (cerrar = apagar)" /d "%SIM_B%" /min cmd /k python "%SIM_B%\sesion_aura_web.py" %*

rem Espera hasta 20 s a que responda (la primera vez Flask tarda un poco).
for /l %%i in (1,1,20) do (
    rem ~1 s de espera (timeout falla si la entrada no es un teclado)
    ping -n 2 127.0.0.1 >nul
    curl -s -o nul %URL%/api/estado && goto abrir
)
echo El servidor no respondio en 20 s. Revisa la ventana "Servidor sesion AURA".
pause
exit /b 1

:abrir
start "" %URL%
