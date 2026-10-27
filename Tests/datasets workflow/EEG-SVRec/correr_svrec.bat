@echo off
rem Abre la corrida completa de H1 con EEG-SVRec en su propia ventana (consola flotante).
rem Se puede cerrar y volver a lanzar: retoma desde la cache. El avance también queda en results\progreso.log
start "H1 EEG-SVRec - progreso" cmd /k "chcp 65001 >nul & set PYTHONIOENCODING=utf-8 & python "%~dp0h1_svrec.py" "C:/Users/ricar/Documents/Repositorios/Datasets/MIRAI/EEG-SVRec""
