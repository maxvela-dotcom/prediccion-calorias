# Guía de uso — Escuela de Fútbol (app compartida en la red local)

<!-- Willys_IA: arranque real, primer administrador, altas, HTTPS, respaldo y demo. -->

## 1. Antes de empezar (una sola vez)

1. La PC que hace de servidor debe estar en la **misma red** que la laptop y los celulares.
   Sirve **cualquier WiFi** (la de la escuela, la de tu casa, un hotspot del celular) o un cable;
   no está atada a un nombre de red concreto.
2. **Arranque rápido en Windows:** doble clic en `iniciar_escuela.bat` (en la carpeta del proyecto).
   El script busca el entorno virtual, instala dependencias si faltan y arranca el servidor.
   Manualmente sería:

   ```powershell
   ..\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ..\.venv\Scripts\python.exe src\main.py
   ```

3. **Habilita la red (una sola vez):** doble clic en `preparar_red.bat` y acepta el pedido de
   administrador. Abre los puertos **5000** (HTTP) y **5443** (HTTPS) en el Firewall de Windows
   **para todos los perfiles de red** (Público, Privado y Dominio), así funciona en cualquier WiFi.
   También agrega una regla para el `python.exe` del proyecto, porque algunos Windows bloquean
   Python aunque el puerto esté abierto. Equivalente manual, en PowerShell como administrador:

   ```powershell
   New-NetFirewallRule -DisplayName "Escuela Flask 5000" -Direction Inbound `
     -Protocol TCP -LocalPort 5000 -Action Allow -Profile Any
   New-NetFirewallRule -DisplayName "Escuela Flask 5443" -Direction Inbound `
     -Protocol TCP -LocalPort 5443 -Action Allow -Profile Any
   ```

4. La consola muestra algo así:

   ```
   🆕 La base está vacía: crea el administrador en el primer arranque.
   👉 Configuración:    http://127.0.0.1:5000/escuela/setup
   👉 Desde el celular: http://192.168.1.25:5000/escuela/setup
   🔒 HTTPS en LAN:     https://192.168.1.25:5443/escuela
   🔐 Certificado CA:   https://192.168.1.25:5443/ca.crt
   ```

   Anota la **IP de LAN** (puede cambiar si la PC se reconecta a la red).

> **WiFi de escuela/institución:** muchas redes bloquean la comunicación directa entre
> dispositivos (*aislamiento de clientes*). Si los celulares no abren la página aunque el
> firewall esté abierto, prueba con un **hotspot del celular** o un router propio para la demo.

## 2. Primer arranque: la base empieza en cero

La primera vez **no hay usuarios, alumnos, sesiones ni pagos**. Abre:

```
http://127.0.0.1:5000/escuela/setup
```

Crea el **administrador** con nombre, usuario y contraseña (mínimo 6 caracteres).
El setup también crea el catálogo mínimo si está vacío:

| Sedes | Categorías | Tarifa mensual |
| :--- | :--- | ---: |
| Sede Central | Sub-8 | 400 Bs |
| Sede Norte | Sub-15 | 500 Bs |
| | Sub-18 | 600 Bs |

Después del setup entras directo al panel. Las sedes y categorías se pueden ampliar en
**Altas y cuentas**.

> Si ya existe al menos una cuenta, `/escuela/setup` redirige al login para evitar un segundo
> administrador.

## 3. Altas de alumnos y cuentas

En el panel, pestaña **Altas y cuentas** (solo `ADMIN`):

- **Nuevo alumno:** nombre, sede, categoría y beca. Genera un QR único `EF-XXXXXXXX`.
- **Cuenta del alumno (opcional):** si completas usuario y contraseña, el alumno puede entrar y
  ver solo su QR, sus asistencias/faltas y su cobro.
- **Cuenta de personal:** crea `ADMIN` o `ENTRENADOR` con su propia contraseña.
- **Sedes y categorías:** agrega nuevas sedes o categorías con su tarifa.
- **Cuentas creadas:** lista todas las cuentas y permite **cambiar la contraseña**.
- **Dar de baja:** el alumno pasa a `INACTIVO`; conserva su historial y ya no registra asistencia.

| Rol | Qué puede hacer |
| :--- | :--- |
| `ADMIN` | Todo: altas, cuentas, asistencia, avisos, cobros, QR y respaldo |
| `ENTRENADOR` | Asistencia, avisos y QR. **No** ve cobros ni gestiona cuentas |
| `ALUMNO` | Solo su QR, sus faltas y su cobro (solo lectura) |

## 4. HTTPS, cámara y PWA

El servidor levanta **HTTP en 5000** y **HTTPS en 5443** al mismo tiempo.

1. En el celular abre primero `https://IP_DE_LA_PC:5443/ca.crt`.
   El navegador mostrará una advertencia porque la CA es local: acepta continuar y descarga el archivo.
2. Instala el certificado como **CA de confianza**:
   - **Android:** Ajustes → Seguridad → Cifrado y credenciales → Instalar certificado → Certificado CA.
   - **iPhone/iPad:** Ajustes → Perfil descargado → Instalar; luego Ajustes → General → Información →
     Ajustes de confianza de certificados → activa la confianza total.
3. Abre `https://IP_DE_LA_PC:5443/escuela`. Sin advertencias, Chrome/Edge ya permite:
   - instalar la PWA (**Instalar app** o «Añadir a pantalla de inicio»),
   - usar la cámara para escanear QR,
   - registrar el service worker para abrir la app sin internet.

> **Si aparece «La conexión no es privada» en la PC**, es porque Windows no tiene instalada la CA
> de la escuela. No es un ataque: el tráfico sí va cifrado. Tienes dos opciones:
>
> 1. **Lo más simple:** en la PC abre `http://127.0.0.1:5000/escuela`. `localhost` cuenta como
>    contexto seguro, así que la cámara y la PWA funcionan igual y no hay ningún aviso.
> 2. **Usar HTTPS también en la PC:** doble clic en `instalar_ca_windows.bat` y acepta el aviso de
>    Windows con **Sí**. Luego cierra todas las ventanas de Chrome/Edge y vuelve a abrir la página.
>
> En el celular ese aviso **no aparece** si usas la APK (ya lleva la CA) o si instalaste `ca.crt`
> como en los pasos 1 y 2.

> El certificado del servidor incluye **todas las IPs de la PC** (WiFi, cable, adaptadores
> virtuales), así que funciona igual en cualquier red. Si la PC cambia de IP al cambiar de WiFi,
> el servidor lo detecta en unos segundos, **regenera solo el certificado del servidor** y
> reinicia HTTPS conservando la misma CA. No hace falta reinstalar `ca.crt` en los celulares:
> solo actualizar la dirección en la APK o el navegador con la IP nueva que muestra la consola.
>
> Si no quieres instalar una CA local, la alternativa es un túnel HTTPS con certificado válido
> (por ejemplo `cloudflared`), que queda fuera de esta entrega.

### 4.1 APK de Android (recomendado para celulares)

La APK es un **cliente WebView**: no guarda datos en el celular, solo abre el panel de la PC.
La base sigue siendo una sola SQLite en la PC.

1. Copia `android/dist/EscuelaUAB.apk` al celular (USB, WhatsApp, Google Drive, etc.) e instálala.
   Android pedirá permitir «instalar apps de origen desconocido» para esa app de mensajería/archivos.
2. Abre **Escuela UAB**. La primera vez pide la dirección del servidor:
   `https://IP_DE_LA_PC:5443/escuela` (por ejemplo `https://192.168.1.25:5443/escuela`).
   Puedes escribir solo `192.168.1.25:5443` y la app agrega `https://` y `/escuela`.
3. La APK **ya incluye la CA local**, así que no necesitas instalar el certificado para usarla.
   Si el certificado cambió, la app muestra un aviso y permite continuar (lo recuerda por servidor).
4. Menú **⋮**: Recargar, Cambiar servidor, Certificado de la escuela, Abrir en el navegador y Acerca de.
5. La cámara se pide la primera vez que tocas **Escanear QR**. Si el equipo no soporta el escáner
   del WebView, usa la marca manual o escribe el código `EF-...`.
6. Los respaldos descargados desde el panel se guardan en **Descargas/EscuelaUAB/**.

Para recompilar la APK en la PC (Android Studio ya instalado):

```powershell
cd android
powershell -ExecutionPolicy Bypass -File .\build_apk.ps1 -Clean
```

> Guarda `android/keystore/escuela.jks` y su contraseña (`escuela2026`, alias `escuela`).
> Sin esa clave no podrás instalar actualizaciones encima de la app ya instalada: habría que
> desinstalarla primero. Si regeneras la CA (`src/certs/`), vuelve a compilar la APK para que
> incluya el nuevo `ca.crt`.

### 4.2 Cambiar de red WiFi

La app **no está atada** a la WiFi de la escuela: funciona en cualquier red donde estén la PC y los
celulares. Al cambiar de red solo cambia la IP de la PC.

1. Conecta la PC a la nueva WiFi (o comparte el hotspot del celular y conecta la PC a él).
2. Mira la consola del servidor. Al detectar la red nueva en unos segundos muestra:

   ```
   🔄 Cambió la red: certificado HTTPS actualizado.
      https://192.168.1.25:5443/escuela
   ```

   Si el servidor estaba detenido, vuelve a abrirlo con `iniciar_escuela.bat`: la IP aparece en
   **En WiFi/LAN**.
3. En cada celular, abre la APK y usa **⋮ → Cambiar servidor** con la IP nueva, por ejemplo
   `https://192.168.1.25:5443/escuela`.
4. La **CA no cambia**, así que no hay que reinstalar el certificado ni la APK.

> Si es la primera vez que usas esa red, ejecuta `preparar_red.bat` **como administrador**: las
> reglas del Firewall se crean para todos los perfiles (Público, Privado y Dominio), así que no
> dependen del nombre de la red. Algunas redes institucionales aíslan a los dispositivos entre sí;
> en ese caso usa un hotspot o un router propio.

## 5. Flujo diario

### Entrenador
1. Abre `https://IP_DE_LA_PC:5443/escuela` e ingresa con su cuenta.
2. Abre o reutiliza la sesión de su sede/categoría.
3. Registra asistencia con el **QR** o con **marca manual** desde la lista de ausentes.
4. Genera los **avisos** de los ausentes.

### Administrador
1. Revisa asistencias y avisos (los cambios se ven al instante porque hay una sola SQLite).
2. Copia el mensaje de un aviso y márcalo como **enviado**.
3. En **Cobros del mes** revisa el monto calculado y marca **PAGADO** o **PENDIENTE**.
4. En **Altas y cuentas** da de alta alumnos, cuentas y catálogo.

### Alumno
1. Entra con la cuenta que le creó el administrador.
2. Ve su QR, el resumen del mes, su cobro y su historial de solo lectura.

## 6. Respaldo

- **Automático:** cada vez que arranca el servidor se guarda una copia del día en
  `data/respaldos/escuela-AAAAMMDD.db` (se conservan los últimos 10). No se repite si ya existe
  la copia de hoy y no se crea mientras la base no tenga cuentas.
- **Desde el panel:** **Altas y cuentas → Descargar respaldo (.db)**. La descarga usa la API de
  backup de SQLite, así que es una copia consistente aunque haya gente registrando asistencia.
- También puedes copiar el archivo `data/app.db` con el servidor detenido.
- Guarda una copia fuera de la PC (USB, nube de la escuela) al menos una vez por semana.
- Antes de un cambio grande, usa el botón de respaldo o detén el servidor y copia `data/app.db`.

## 7. Reiniciar el servidor

```powershell
Get-NetTCPConnection -LocalPort 5000,5443 -State Listen -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
..\.venv\Scripts\python.exe src\main.py
```

## 8. Qué **no** prometer en esta entrega

- La APK es un **cliente WebView**: requiere que la PC esté encendida y en la **misma red**
  (cualquier WiFi, hotspot o cable). No funciona offline ni guarda datos propios.
- No funciona si la PC y el celular están en redes distintas (por ejemplo, uno en datos móviles y
  otro en WiFi) sin un túnel HTTPS.
- La instalación de la PWA en Android exige instalar antes la CA local; con `http://IP` Chrome no
  registra el service worker ni garantiza la cámara. La marca manual siempre está disponible.
  (La APK no necesita instalar la CA: ya la lleva dentro).
- El respaldo automático es **diario y al arrancar**, no una tarea programada cada hora; si la PC
  queda encendida varios días, el respaldo se actualiza cuando reinicias el servidor.
- Las recuperaciones, la cuarta falta y las aprobaciones del director siguen fuera del MVP.

## 9. Modo local aislado (opcional)

`/escuela?modo=local` conserva la demo con **IndexedDB** en el dispositivo, sin usar la SQLite de la
PC. Sirve para mostrar la app sin red, pero **no comparte datos** con la base real.
