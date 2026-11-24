@echo off
rem Willys_IA: arranca la app compartida de la Escuela de Futbol.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar_escuela.ps1"
if errorlevel 1 pause
