# ============================================================================
#  Escuela de Futbol - Preparar la red para los celulares (Willys_IA)
#  Uso: doble clic en preparar_red.bat (pedira permisos de administrador)
# ============================================================================
$ErrorActionPreference = "Stop"

$esAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $esAdmin) {
    Write-Host "Se necesitan permisos de administrador. Abriendo ventana elevada..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSCommandPath`""
    )
    exit 0
}

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Green
Write-Host "  PREPARAR LA RED PARA LA ESCUELA" -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Green
Write-Host ""

foreach ($puerto in @(5000, 5443)) {
    $nombre = "Escuela Flask $puerto"
    Get-NetFirewallRule -DisplayName $nombre -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction SilentlyContinue
    # -Profile Any = funciona en CUALQUIER red: WiFi de la escuela, otra WiFi,
    # hotspot del celular o cable. No depende del nombre de la red.
    New-NetFirewallRule `
        -DisplayName $nombre `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort $puerto `
        -Action Allow `
        -Profile Any `
        -Enabled True | Out-Null
    Write-Host "OK  Puerto $puerto habilitado en cualquier red." -ForegroundColor Green
}

# Regla extra por programa: algunos Windows bloquean Python aunque el puerto
# este abierto. Se agrega el ejecutable del entorno virtual (si existe).
$Raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
$Padre = Split-Path -Parent $Raiz
$Python = @(
    (Join-Path $Padre ".venv\Scripts\python.exe"),
    (Join-Path $Raiz ".venv\Scripts\python.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($Python) {
    $nombrePython = "Escuela Python"
    Get-NetFirewallRule -DisplayName $nombrePython -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction SilentlyContinue
    New-NetFirewallRule `
        -DisplayName $nombrePython `
        -Direction Inbound `
        -Program $Python `
        -Action Allow `
        -Profile Any `
        -Enabled True | Out-Null
    Write-Host "OK  Python habilitado: $Python" -ForegroundColor Green
}

Write-Host ""
Write-Host "IPs de esta PC (usa la que corresponda a la red actual):" -ForegroundColor Cyan
Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.InterfaceAlias -notlike "*Loopback*"
    } |
    ForEach-Object {
        Write-Host ("   {0,-16} {1}" -f $_.IPAddress, $_.InterfaceAlias)
    }

Write-Host ""
Write-Host "Reglas creadas. La app ya puede recibir conexiones de los celulares" -ForegroundColor Green
Write-Host "en cualquier WiFi, hotspot o cable." -ForegroundColor Green
Write-Host ""
Write-Host "Si los celulares siguen sin conectar:" -ForegroundColor Cyan
Write-Host "  1. Verifica que esten en la MISMA red que la PC."
Write-Host "  2. Muchas redes de escuela/institucion bloquean la comunicacion"
Write-Host "     entre dispositivos (aislamiento de clientes). En ese caso usa"
Write-Host "     un hotspot del celular o un router propio para la demo."
Write-Host "  3. La IP de la PC puede cambiar al cambiar de red: mirala en la"
Write-Host "     ventana del servidor (se muestra al arrancar)."
Write-Host ""
Read-Host "Presiona ENTER para cerrar"
