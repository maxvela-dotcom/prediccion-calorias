# ============================================================================
#  Escuela de Futbol - Iniciar el servidor compartido (Willys_IA)
#  Uso: doble clic en iniciar_escuela.bat
# ============================================================================
$ErrorActionPreference = "Stop"

$Raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
$Padre = Split-Path -Parent $Raiz

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Green
Write-Host "  ESCUELA DE FUTBOL - SERVIDOR COMPARTIDO" -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Green
Write-Host ""

# 1) Localizar (o crear) el entorno virtual.
$Candidatos = @(
    (Join-Path $Padre ".venv\Scripts\python.exe"),
    (Join-Path $Raiz ".venv\Scripts\python.exe")
)
$Python = $null
foreach ($candidato in $Candidatos) {
    if (Test-Path $candidato) { $Python = $candidato; break }
}

if (-not $Python) {
    $PythonBase = (Get-Command python -ErrorAction SilentlyContinue)
    if (-not $PythonBase) {
        Write-Host "ERROR: no se encontro Python. Instala Python 3.11 o superior." -ForegroundColor Red
        Write-Host "Descarga: https://www.python.org/downloads/"
        Read-Host "Presiona ENTER para cerrar"
        exit 1
    }
    $DestinoVenv = Join-Path $Raiz ".venv"
    Write-Host "Creando entorno virtual en $DestinoVenv ..."
    & $PythonBase.Source -m venv $DestinoVenv
    $Python = Join-Path $DestinoVenv "Scripts\python.exe"
}

# 2) Verificar dependencias (Flask, segno, cryptography).
& $Python -c "import flask, segno, cryptography" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Instalando dependencias (solo la primera vez)..." -ForegroundColor Yellow
    & $Python -m pip install --upgrade pip
    & $Python -m pip install -r (Join-Path $Raiz "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: no se pudieron instalar las dependencias." -ForegroundColor Red
        Read-Host "Presiona ENTER para cerrar"
        exit 1
    }
}

# 3) Recordatorio de red (solo informativo).
$ReglasFirewall = Get-NetFirewallRule -DisplayName "Escuela Flask *" -ErrorAction SilentlyContinue
if (-not $ReglasFirewall) {
    Write-Host "AVISO: el Firewall de Windows todavia no permite los puertos 5000/5443." -ForegroundColor Yellow
    Write-Host "Ejecuta preparar_red.bat como administrador (una sola vez)." -ForegroundColor Yellow
    Write-Host ""
}
Write-Host "Funciona en cualquier WiFi, hotspot o cable: PC y celulares en la misma red." -ForegroundColor Cyan
Write-Host "Si los celulares no conectan, ejecuta preparar_red.bat como administrador." -ForegroundColor Cyan
Write-Host ""

# 4) Arrancar el servidor (HTTP 5000 + HTTPS 5443).
try {
    & $Python (Join-Path $Raiz "src\main.py")
} finally {
    Write-Host ""
    Write-Host "El servidor se detuvo." -ForegroundColor Yellow
    Read-Host "Presiona ENTER para cerrar"
}
