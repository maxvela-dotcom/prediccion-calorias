# =====================================================================
#  Compila la APK de la Escuela UAB sin Gradle.
#
#  Usa las herramientas que ya vienen con Android Studio:
#    aapt2, javac, d8, zipalign, apksigner y keytool.
#
#  Uso:
#    .\build_apk.ps1
#    .\build_apk.ps1 -Clean
#
#  Resultado:
#    android\dist\EscuelaUAB.apk
#
#  Importante: guarda android\keystore\escuela.jks y su contraseña.
#  Sin esa clave no podrás instalar actualizaciones sobre la app ya
#  instalada en los celulares.
# =====================================================================
param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $raiz

$keystore = Join-Path $raiz "keystore\escuela.jks"
$alias = "escuela"
$claveKeystore = "escuela2026"
$apkFinal = Join-Path $raiz "dist\EscuelaUAB.apk"

function Verificar($codigo, $paso) {
    if ($codigo -ne 0) {
        throw "Error en $paso (codigo de salida $codigo)."
    }
}

function Buscar-JavaHome {
    $candidatos = @()
    if ($env:JAVA_HOME) { $candidatos += $env:JAVA_HOME }
    $candidatos += @(
        "C:\Program Files\Android\Android Studio\jbr",
        (Join-Path $env:LOCALAPPDATA "Programs\Android Studio\jbr"),
        "C:\Program Files\Java\jdk-17",
        "C:\Program Files\Java\jdk-21"
    )
    foreach ($candidato in $candidatos) {
        if ($candidato -and (Test-Path (Join-Path $candidato "bin\javac.exe"))) {
            return $candidato
        }
    }
    throw "No se encontro un JDK con javac. Instala Android Studio o define JAVA_HOME."
}

# --- 1. Localizar JDK y Android SDK ---------------------------------
$javaHome = Buscar-JavaHome
$env:JAVA_HOME = $javaHome
$env:Path = (Join-Path $javaHome "bin") + ";" + $env:Path

$sdk = $env:ANDROID_HOME
if (-not $sdk -or -not (Test-Path $sdk)) {
    $sdk = $env:ANDROID_SDK_ROOT
}
if (-not $sdk -or -not (Test-Path $sdk)) {
    $sdk = Join-Path $env:LOCALAPPDATA "Android\Sdk"
}
if (-not (Test-Path $sdk)) {
    throw "No se encontro el Android SDK. Abre Android Studio > SDK Manager e instala Build-Tools y una plataforma."
}

$buildTools = Get-ChildItem (Join-Path $sdk "build-tools") -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName "aapt2.exe") } |
    Sort-Object { [version]($_.Name -replace "[^0-9.]", "") } -Descending |
    Select-Object -First 1
if (-not $buildTools) {
    throw "No hay Build-Tools con aapt2 en $sdk\build-tools."
}

$plataformas = Get-ChildItem (Join-Path $sdk "platforms") -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName "android.jar") } |
    Sort-Object { [int](($_.Name -split "-")[-1] -replace "[^0-9]", "") } -Descending
if (-not $plataformas) {
    throw "No hay plataformas Android con android.jar en $sdk\platforms."
}
$androidJar = Join-Path $plataformas[0].FullName "android.jar"

$aapt2 = Join-Path $buildTools.FullName "aapt2.exe"
$d8 = Join-Path $buildTools.FullName "d8.bat"
$zipalign = Join-Path $buildTools.FullName "zipalign.exe"
$apksigner = Join-Path $buildTools.FullName "apksigner.bat"
$javac = Join-Path $javaHome "bin\javac.exe"
$keytool = Join-Path $javaHome "bin\keytool.exe"

Write-Host ""
Write-Host "=== Escuela UAB - compilacion de APK ===" -ForegroundColor Cyan
Write-Host "JDK:          $javaHome"
Write-Host "Build-Tools:  $($buildTools.Name)"
Write-Host "Plataforma:   $($plataformas[0].Name)"
Write-Host ""

# --- 2. Sincronizar icono y CA local --------------------------------
$origenIcono = Join-Path $raiz "..\src\static\icons\icon-192.png"
$origenCA = Join-Path $raiz "..\src\certs\ca.crt"
$destinoIcono = Join-Path $raiz "res\mipmap-xxxhdpi\ic_launcher.png"
$destinoCA = Join-Path $raiz "res\raw\ca_escuela.crt"

if (Test-Path $origenIcono) {
    Copy-Item $origenIcono $destinoIcono -Force
} elseif (-not (Test-Path $destinoIcono)) {
    throw "Falta el icono: $destinoIcono"
}

if (Test-Path $origenCA) {
    Copy-Item $origenCA $destinoCA -Force
    Write-Host "CA local incluida en la APK: $origenCA"
} elseif (Test-Path $destinoCA) {
    Write-Host "Aviso: no existe src\certs\ca.crt; se usa la CA ya copiada en res\raw." -ForegroundColor Yellow
} else {
    throw "No se encontro la CA local. Inicia el servidor una vez para generarla."
}

# --- 3. Preparar carpetas -------------------------------------------
$compilado = Join-Path $raiz "build"
if ($Clean -and (Test-Path $compilado)) {
    Remove-Item -Recurse -Force $compilado
}
$dirRes = Join-Path $compilado "res"
$dirGen = Join-Path $compilado "gen"
$dirClases = Join-Path $compilado "classes"
$dirDex = Join-Path $compilado "dex"
New-Item -ItemType Directory -Force -Path $dirRes, $dirGen, $dirClases, $dirDex, (Join-Path $raiz "dist") | Out-Null

$resZip = Join-Path $compilado "res.zip"
$baseApk = Join-Path $compilado "base.apk"
$unalignedApk = Join-Path $compilado "unaligned.apk"
$alignedApk = Join-Path $compilado "aligned.apk"

# --- 4. Compilar y enlazar recursos --------------------------------
Write-Host "[1/7] Compilando recursos (aapt2)..."
& $aapt2 compile --dir (Join-Path $raiz "res") -o $resZip
Verificar $LASTEXITCODE "aapt2 compile"

Write-Host "[2/7] Enlazando recursos y manifiesto..."
& $aapt2 link `
    -o $baseApk `
    -I $androidJar `
    --manifest (Join-Path $raiz "AndroidManifest.xml") `
    -R $resZip `
    --java $dirGen `
    --auto-add-overlay `
    --min-sdk-version 24 `
    --target-sdk-version 34 `
    --version-code 1 `
    --version-name "1.0"
Verificar $LASTEXITCODE "aapt2 link"

# --- 5. Compilar Java y convertir a DEX -----------------------------
Write-Host "[3/7] Compilando Java (javac --release 17)..."
$fuentes = @()
$fuentes += Get-ChildItem (Join-Path $raiz "java") -Recurse -Filter *.java | ForEach-Object { $_.FullName }
$fuentes += Get-ChildItem $dirGen -Recurse -Filter *.java | ForEach-Object { $_.FullName }

$argumentosJavac = @("--release", "17", "-encoding", "UTF-8", "-classpath", $androidJar, "-d", $dirClases) + $fuentes
& $javac $argumentosJavac
Verificar $LASTEXITCODE "javac"

Write-Host "[4/7] Generando classes.dex (d8)..."
$clases = Get-ChildItem $dirClases -Recurse -Filter *.class | ForEach-Object { $_.FullName }
$argumentosD8 = @("--release", "--min-api", "24", "--lib", $androidJar, "--output", $dirDex) + $clases
& $d8 $argumentosD8
Verificar $LASTEXITCODE "d8"

# --- 6. Empaquetar la APK ------------------------------------------
Write-Host "[5/7] Empaquetando classes.dex..."
Copy-Item $baseApk $unalignedApk -Force

# Se usa .NET para agregar el dex sin recomprimir resources.arsc
# (Android 11+ exige que resources.arsc quede sin comprimir).
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open($unalignedApk, [System.IO.Compression.ZipArchiveMode]::Update)
try {
    $entrada = $zip.CreateEntry("classes.dex", [System.IO.Compression.CompressionLevel]::Optimal)
    $flujo = $entrada.Open()
    try {
        $dex = [System.IO.File]::ReadAllBytes((Join-Path $dirDex "classes.dex"))
        $flujo.Write($dex, 0, $dex.Length)
    } finally {
        $flujo.Close()
    }
} finally {
    $zip.Dispose()
}

Write-Host "[6/7] Alineando la APK (zipalign)..."
& $zipalign -f -p 4 $unalignedApk $alignedApk
Verificar $LASTEXITCODE "zipalign"

# --- 7. Firmar la APK ----------------------------------------------
if (-not (Test-Path $keystore)) {
    Write-Host "[7/7] Creando keystore de firma..."
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $keystore) | Out-Null
    & $keytool -genkeypair `
        -keystore $keystore `
        -alias $alias `
        -keyalg RSA `
        -keysize 2048 `
        -validity 10000 `
        -storepass $claveKeystore `
        -keypass $claveKeystore `
        -dname "CN=Escuela de Futbol UAB, O=Universidad Adventista de Bolivia, C=BO"
    Verificar $LASTEXITCODE "keytool"
} else {
    Write-Host "[7/7] Usando keystore existente..."
}

& $apksigner sign `
    --ks $keystore `
    --ks-key-alias $alias `
    --ks-pass "pass:$claveKeystore" `
    --key-pass "pass:$claveKeystore" `
    --out $apkFinal `
    $alignedApk
Verificar $LASTEXITCODE "apksigner sign"

& $apksigner verify --verbose --print-certs $apkFinal
Verificar $LASTEXITCODE "apksigner verify"

$tamano = [math]::Round((Get-Item $apkFinal).Length / 1MB, 2)
Write-Host ""
Write-Host "APK lista: $apkFinal ($tamano MB)" -ForegroundColor Green
Write-Host "Clave del keystore: $claveKeystore (alias $alias)" -ForegroundColor Yellow
Write-Host "Guarda android\keystore\escuela.jks para firmar futuras actualizaciones." -ForegroundColor Yellow
Write-Host ""
