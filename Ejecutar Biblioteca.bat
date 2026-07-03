@echo off
setlocal

cd /d "%~dp0sociomatic\sociomatic\biblioteca_python"

start "" "http://127.0.0.1:8765"
python server.py

pause
