@echo off
rem Willys_IA: instala la CA local en el usuario actual de Windows.
rem Permite abrir https://IP:5443/escuela en Chrome/Edge sin el aviso.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_ca_windows.ps1"
if errorlevel 1 pause
