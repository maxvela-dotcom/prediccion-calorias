@echo off
rem Willys_IA: abre los puertos 5000 y 5443 en el Firewall de Windows.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0preparar_red.ps1"
if errorlevel 1 pause
