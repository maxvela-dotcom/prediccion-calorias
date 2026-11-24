# ============================================================================
#  Escuela de Futbol - Instalar la CA local en Windows (Willys_IA)
#  Uso: doble clic en instalar_ca_windows.bat
#
#  Hace que Chrome y Edge de ESTA PC abran https://IP:5443/escuela sin el
#  aviso "La conexion no es privada". Solo afecta al usuario actual y se
#  puede deshacer (ver el final del mensaje).
# ============================================================================
$ErrorActionPreference = "Stop"

$Raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
$Certificado = Join-Path $Raiz "src\certs\ca.crt"

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Green
Write-Host "  INSTALAR CERTIFICADO DE LA ESCUELA EN WINDOWS" -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Green
Write-Host ""

if (-not (Test-Path $Certificado)) {
    Write-Host "No se encontro el certificado:" -ForegroundColor Red
    Write-Host "  $Certificado" -ForegroundColor Red
    Write-Host "Arranca el servidor al menos una vez para generarlo." -ForegroundColor Yellow
    Read-Host "Presiona ENTER para cerrar"
    exit 1
}

$ca = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 $Certificado
$almacen = New-Object System.Security.Cryptography.X509Certificates.X509Store "Root", "CurrentUser"
$almacen.Open("ReadWrite")

$yaInstalada = $almacen.Certificates | Where-Object { $_.Thumbprint -eq $ca.Thumbprint }
if ($yaInstalada) {
    Write-Host "La CA ya estaba instalada en este usuario." -ForegroundColor Cyan
} else {
    # Windows puede mostrar un aviso de seguridad: hay que aceptar con "Si".
    # Es normal: se esta confiando en la autoridad local del proyecto.
    $almacen.Add($ca)
    Write-Host "CA instalada correctamente." -ForegroundColor Green
}

$almacen.Close()

Write-Host ""
Write-Host "Huella SHA1: $($ca.Thumbprint)" -ForegroundColor DarkGray
Write-Host "Titular:     $($ca.Subject)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Cierra TODAS las ventanas de Chrome/Edge y vuelve a abrirlas." -ForegroundColor Yellow
Write-Host "Luego entra a https://IP_DE_LA_PC:5443/escuela (ya sin aviso)." -ForegroundColor Yellow
Write-Host ""
Write-Host "En el celular no hace falta esto: la APK ya incluye la CA." -ForegroundColor Cyan
Write-Host "Para quitarla: certutil -user -delstore Root $($ca.Thumbprint)" -ForegroundColor DarkGray
Write-Host ""
Read-Host "Presiona ENTER para cerrar"
