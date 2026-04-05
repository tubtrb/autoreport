@echo off
setlocal

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if exist "%PYTHON_EXE%" goto run

set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if exist "%PYTHON_EXE%" goto run

set "PYTHON_EXE=python"

:run
"%PYTHON_EXE%" -m autoreport.web.serve public --host 0.0.0.0 --port 8000 %*

