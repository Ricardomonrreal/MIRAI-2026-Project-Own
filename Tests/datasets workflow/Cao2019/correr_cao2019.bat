@echo off
rem Corrida completa del control positivo H1b (Cao 2019) en su propia ventana. Retoma desde la cache.
start "H1b Cao2019 - progreso" cmd /k "chcp 65001 >nul & set PYTHONIOENCODING=utf-8 & python "%~dp0h1b_cao2019.py" "C:/Users/ricar/Documents/Repositorios/Datasets/MIRAI/Cao2019""
