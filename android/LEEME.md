# APK de la Escuela UAB

Cliente Android de la Escuela de Fútbol UAB. Es un **contenedor WebView**: la app no guarda
alumnos, asistencias ni pagos en el celular. Todo sigue en la PC (Flask + SQLite) y el celular
se conecta por la misma red: cualquier WiFi, hotspot del celular o cable.

- **APK lista:** `dist/EscuelaUAB.apk`
- **Paquete:** `bo.uab.escuela`
- **Versión:** 1.0 (versionCode 1)
- **Android mínimo:** 7.0 (API 24) · **objetivo:** Android 14 (API 34)
- **Firma:** v2 + v3 con `keystore/escuela.jks` (alias `escuela`, contraseña `escuela2026`)

## Instalar en el celular

1. Copia `dist/EscuelaUAB.apk` al celular (USB, WhatsApp, Drive, etc.).
2. Abre el archivo e instala. Android pedirá permitir «instalar apps de origen desconocido» para la
   app desde la que abriste el APK.
3. Abre **Escuela UAB** y escribe la dirección del servidor:
   `https://IP_DE_LA_PC:5443/escuela`
   También puedes escribir solo `IP:5443` (la app agrega `https://` y `/escuela`).
4. Inicia sesión con la cuenta creada en la PC.

La APK **ya lleva la CA local** (`res/raw/ca_escuela.crt`), por lo que no hace falta instalar el
certificado para usarla. Si la CA cambió, Android muestra el aviso de certificado y la app permite
continuar; el permiso se recuerda por servidor.

## Menú de la app

| Opción | Qué hace |
| :--- | :--- |
| Recargar | Vuelve a cargar el panel |
| Cambiar servidor | Edita la IP/puerto/ruta y la guarda |
| Certificado de la escuela | Explica la CA incluida y abre `/ca.crt` en el navegador |
| Abrir en el navegador | Abre la misma URL en Chrome/Edge (útil para instalar la PWA) |
| Acerca de | Versión y alcance |

La cámara se pide la primera vez que se toca **Escanear QR**. Si el WebView del equipo no soporta
`BarcodeDetector`, usa la lista de ausentes o escribe el código `EF-...` manualmente.

Los respaldos descargados desde el panel se guardan en **Descargas/EscuelaUAB/**.

## Recompilar

Requisitos: Android Studio instalado (SDK + Build-Tools + JBR). No hace falta Gradle ni internet.

```powershell
cd android
powershell -ExecutionPolicy Bypass -File .\build_apk.ps1 -Clean
```

El script:

1. copia el icono (`src/static/icons/icon-192.png`) y la CA (`src/certs/ca.crt`) a `res/`;
2. compila recursos con `aapt2`;
3. compila `MainActivity.java` con `javac --release 17`;
4. genera `classes.dex` con `d8 --min-api 24`;
5. empaqueta el dex sin recomprimir `resources.arsc`;
6. alinea con `zipalign` y firma con `apksigner`;
7. verifica la firma y deja `dist/EscuelaUAB.apk`.

La primera vez crea `keystore/escuela.jks`. **Guárdalo junto con su contraseña**: si se pierde, no
podrás instalar actualizaciones encima de la app ya instalada (habría que desinstalarla y perder los
datos locales, que en esta app son solo la URL y los hosts aceptados).

## Si cambia la IP de la PC

1. El servidor conserva la **misma CA** y regenera solo el certificado del servidor al arrancar.
2. En el celular: **⋮ → Cambiar servidor** y escribe la nueva IP.
3. No hace falta reinstalar la APK ni el certificado.

Si se borra `src/certs/` y se crea una CA nueva, hay que recompilar la APK para que incluya el nuevo
`ca.crt` (o aceptar el aviso de certificado una vez en cada celular).

## Problemas frecuentes

| Síntoma | Causa / solución |
| :--- | :--- |
| «Sin conexión con la escuela» | PC apagada, servidor detenido, IP incorrecta o WiFi distinta. Verifica `https://IP:5443/escuela` en el navegador del celular. |
| No conecta aunque la PC responde | Firewall de Windows bloqueando 5443. Ejecuta `preparar_red.bat` como administrador. |
| La WiFi institucional aísla clientes | Usa un hotspot del celular o un router propio para la demo. |
| Aviso de certificado | La CA de la APK no coincide con la del servidor (se regeneró). Continúa una vez o recompila la APK. |
| El escáner QR no abre | El WebView no soporta `BarcodeDetector` o falta permiso de cámara. Revisa Ajustes → Apps → Escuela UAB → Permisos → Cámara; usa la marca manual. |
| No descarga el respaldo | En Android 9 o menor, concede permiso de almacenamiento. En Android 10+ se guarda en Descargas/EscuelaUAB. |

## Estructura

```text
android/
├── AndroidManifest.xml
├── build_apk.ps1
├── java/bo/uab/escuela/MainActivity.java
├── res/
│   ├── mipmap-xxxhdpi/ic_launcher.png
│   ├── raw/ca_escuela.crt
│   ├── values/strings.xml
│   ├── values/styles.xml
│   └── xml/network_security_config.xml
├── keystore/escuela.jks
├── build/                  # intermedios (se puede borrar)
└── dist/EscuelaUAB.apk
```
