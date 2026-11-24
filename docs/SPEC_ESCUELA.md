# docs/SPEC_ESCUELA.md — Contrato del MVP «Asistencias Escuela de Fútbol»
<!-- Willys_IA: Contrato Inviolable de Requerimientos - Taller UAB 2026 -->
<!-- REGLA #2: Lo que no esté definido con certeza se marca [POR DEFINIR], ¡jamás se inventa! -->

> **Alcance de este documento:** solo el módulo **Escuela**. El dominio de ejemplo del starter kit
> (`Calorías en Rutina`) mantiene su propio contrato en `docs/SPEC.md` y **no se modifica**.
> Este módulo vive en `/escuela`, expone su API en `/api/escuela` y usa tablas con prefijo `ef_`.

---

## 1. Descripción del Sistema
> **Resumen Ejecutivo (2 líneas):**
> *Sistema web compartido en la red local para una escuela de fútbol con 200 alumnos, 20 entrenadores,
> 3 categorías y 2 sedes, con los datos en una sola SQLite en la PC.*
> *Administrador, entrenadores y alumnos entran desde su laptop o celular con su propio rol; el
> entrenador registra la asistencia con QR o marca manual, la administradora recibe el aviso de cada
> falta el mismo día y el sistema calcula el cobro mensual de cada alumno.*

---

## 2. Problema y Dolor que Resuelve
- **Situación actual:** 6 cuadernos (3 categorías × 2 sedes), transcripción manual a Excel cada mes,
  2–3 h de cierre mensual y 24–26 h semanales de trabajo administrativo, con alumnos omitidos,
  registros duplicados y cobros errados.
- **Objetivo del MVP:** que una sesión de entrenamiento se registre en segundos, que ninguna falta
  quede sin avisar y que el cobro del mes se calcule solo, sin volver a transcribir nada.

---

## 3. Usuarios y Actores del MVP

| Actor | Rol en el sistema | Permisos en el MVP |
| :--- | :--- | :--- |
| **Entrenador** | Registra la asistencia al inicio del entrenamiento | Login `ENTRENADOR`: abrir/reutilizar la sesión de su sede y categoría, escanear QR, marcar presente a mano, generar avisos y ver QR. **No** ve cobros ni marca pagos |
| **Administrador** | Revisa faltas, contacta al padre y controla cobros | Login `ADMIN`: todo lo del entrenador **más** ver avisos pendientes, marcar aviso como enviado, consultar cobros y marcar pagado/pendiente. Puede usar laptop o celular |
| **Alumno** | Consulta su propio estado desde su celular | Login `ALUMNO`: **solo lectura** de su QR, su historial (asistencias/faltas) y su cobro del mes. No ve datos de otros alumnos |
| **Director** | Autoriza becas, sanciones y excepciones | Fuera del MVP. Sus aprobaciones se registran hoy fuera del sistema (`[POR DEFINIR]` cómo se digitalizan) |
| **Padre** | Recibe el aviso de la falta | Fuera del MVP. Recibe el mensaje que el administrador envía por WhatsApp (`[POR DEFINIR]` acceso propio) |
| **Visitante no autenticado** | — | Redirigido a `/escuela/login`; las APIs responden **401**. La demo aislada `?modo=local` sigue siendo pública a propósito |

> **Primer arranque (base vacía):** no hay credenciales sembradas. Al abrir `/escuela/setup` se crea
> el primer `ADMIN` y el catálogo mínimo (Sede Central, Sede Norte; Sub-8 400 Bs, Sub-15 500 Bs,
> Sub-18 600 Bs). Las demás cuentas se crean desde **Altas y cuentas**.

---

## 4. Alcance Estricto del MVP

### 4.1 LO QUE SÍ HACE
- [x] **RF-E01 (Registrar asistencia):** abrir o reutilizar una sesión (sede, categoría, fecha, hora,
      entrenador) y registrar la presencia por **QR** o por **marca manual**. Ambas vías son equivalentes.
- [x] **RF-E02 (Avisar la falta):** generar un aviso pendiente por cada ausente de la sesión y
      permitir al administrador marcarlo como **enviado**.
- [x] **RF-E03 (Calcular el cobro):** calcular el monto mensual por alumno según las reglas de negocio,
      listar el resumen facturado/cobrado/pendiente y marcar cada cobro como **pagado** o **pendiente**.
- [x] **RF-E04 (Soporte de la operación):** generar el **QR único** de cada alumno, filtrar estudiantes
      por sede/categoría y operar sin internet con cola local. La base arranca **vacía**: no hay
      alumnos ni usuarios sembrados.
- [x] **RF-E08 (App compartida):** un único servidor en la PC (Flask + **SQLite única**) atiende a todos
      los dispositivos de la **misma red** —cualquier WiFi, hotspot o cable— en
      `http://IP_DE_LA_PC:5000/escuela`. Lo registrado por un entrenador se ve al instante en la
      laptop de la administradora y en el celular del alumno.
- [x] **RF-E09 (Login y roles):** `/escuela/login` autentica contra `ef_usuarios` y guarda la sesión de
      Flask. `ADMIN` (todo), `ENTRENADOR` (asistencia, avisos y QR) y `ALUMNO` (solo su registro).
      Los permisos se validan **en el servidor** (401/403) y además se ocultan en la interfaz.
- [x] **RF-E10 (Vista del alumno):** `/escuela` muestra al rol `ALUMNO` una pantalla de solo lectura con
      su QR, resumen del mes (entrenamientos, asistencias, faltas), su cobro y su historial.
- [x] **RF-E11 (Primer arranque y altas):** la base comienza **completamente vacía**. `/escuela/setup`
      crea el primer `ADMIN` y el catálogo mínimo. El administrador puede registrar alumnos
      manualmente, crear la cuenta de acceso de cada alumno (rol `ALUMNO`), crear cuentas de
      `ADMIN`/`ENTRENADOR`, cambiar contraseñas, agregar sedes/categorías y dar de baja alumnos
      (baja lógica, conservando el historial).
- [x] **RF-E12 (HTTPS local):** el servidor levanta HTTP en `5000` y **HTTPS en `5443`** con una CA
      local y un certificado con las IP de la LAN. Permite instalar la PWA y usar la cámara en los
      celulares; `/ca.crt` descarga la CA para instalarla una vez en cada dispositivo.
- [x] **RF-E13 (Respaldo):** `/escuela/respaldo` descarga una copia consistente de la base (solo
      `ADMIN`) usando la API de backup de SQLite. Además, al arrancar el servidor se guarda una
      copia diaria en `data/respaldos/` (se conservan las últimas 10).

### 4.1.1 Modo app local (demo aislada, se conserva)
- [x] **RF-E05 (App instalable):** el panel es una **PWA**: se instala con ícono propio, abre a pantalla
      completa y la «cáscara» queda en caché (`manifest.webmanifest`, `sw.js`, íconos 192/512).
      El service worker **no** cachea páginas ni APIs para no servir sesiones viejas.
- [x] **RF-E06 (Datos en el celular):** abriendo `?modo=local` **no se usa SQLite**. Una capa local
      (`API_LOCAL`, en `src/static/escuela_local.js`) reproduce las reglas RN-E01 a RN-E07 sobre
      **IndexedDB** (`escuela_futbol_local`). Es una demo aislada: **no comparte datos** con la PC.
- [x] **RF-E07 (Demo local autosuficiente):** solo en `?modo=local`, el primer arranque siembra 24
      alumnos, 6 sesiones hoy y las reglas de avisos/cobros en IndexedDB; «Reiniciar demo» borra la
      base local y la vuelve a crear. **No** toca la SQLite compartida ni crea usuarios del servidor.
- [x] **RF-E14 (APK de Android):** cliente **WebView** en `android/` que abre `https://IP:5443/escuela`
      con URL configurable, cámara, descargas con cookie y CA local incluida en la APK. Se compila y
      firma sin Gradle con `android/build_apk.ps1` (aapt2 + javac + d8 + zipalign + apksigner).

### 4.2 LO QUE QUEDA EXPLÍCITAMENTE FUERA
- ❌ **Comprobante de pago numerado** y su impresión.
- ❌ **Recuperaciones y límite de 3 faltas por mes** (regla de negocio documentada en §6, no implementada).
- ❌ **Aprobaciones y reportes del director.**
- ❌ **Becas y sanciones** como flujo de alta/baja (el cálculo sí respeta `becado = 1`; la beca se
  marca al crear el alumno).
- ❌ **Envío automático de mensajes** (WhatsApp/SMS/correo): el sistema redacta el mensaje, el
      administrador lo copia y lo envía.
- ❌ **Acceso desde internet**: la app compartida funciona solo en la **LAN/WiFi**. Publicarla fuera
  de la escuela exige un túnel HTTPS o un hosting (`[POR DEFINIR]`).
- ❌ **App nativa con datos offline:** la APK es un contenedor WebView; no replica la base en el
  celular ni funciona sin la PC encendida. La demo local de §4.1.1 sigue siendo la única offline.
- ❌ **Control de morosidad**: solo se distingue `PAGADO` de `PENDIENTE`.

---

## 5. Requisitos No Funcionales Medibles

1. **RNF-E01 (Respuesta):** registrar una asistencia responde en **menos de 1 segundo** con los datos
   de demostración.
2. **RNF-E02 (Robustez):** toda entrada inválida (fecha, hora, periodo, IDs inexistentes, duplicados,
   alumno de otra sede/categoría) devuelve un **error controlado** (`ValueError` → HTTP 400/404) sin
   `Traceback` al usuario.
3. **RNF-E03 (Integridad):** las reglas críticas se refuerzan también en la base de datos con
   `PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE` y `CHECK` (ver §7).
4. **RNF-E04 (QR):** cada alumno tiene un token **único e intransferible**. En modo servidor se genera
   con `segno` y se sirve como SVG; en modo app se genera en el dispositivo con `qrcode.js` embebido.
   Ninguno de los dos depende de servicios externos.
5. **RNF-E05 (Operación sin internet):** la app compartida funciona en la **LAN sin salida a internet**.
   En modo local los datos viven en IndexedDB; en modo servidor, si el `POST` falla por red, se guarda
   en `localStorage` y se sincroniza al recuperar conexión (cola heredada del MVP).
6. **RNF-E06 (Trazabilidad):** cada asistencia guarda **método** (`QR` o `MANUAL`) y **fecha/hora de
   registro**; cada aviso guarda cuándo se creó y cuándo se envió.
7. **RNF-E07 (Migraciones):** el esquema se aplica con migraciones versionadas e idempotentes
   (`004_escuela_futbol`, `005_usuarios_escuela`) registradas en `schema_migrations`, compatibles con
   bases existentes.
8. **RNF-E08 (Fuente única de verdad):** existe **una sola SQLite** en la PC (`data/app.db`). Todos los
   dispositivos leen y escriben ahí; no hay copias locales ni sincronización entre celulares.
9. **RNF-E09 (Autorización en servidor):** cada endpoint valida sesión y rol antes de ejecutar la regla
   de negocio. Un `ENTRENADOR` recibe **403** en cobros y en «marcar aviso enviado»; un `ALUMNO` recibe
   **403** fuera de `/api/escuela/mi` y de su propio QR. Ocultar botones en la interfaz es solo refuerzo.
10. **RNF-E10 (Contraseñas):** se guardan con `generate_password_hash` de Werkzeug y nunca se devuelven
    al cliente. La sesión de la escuela es independiente de la sesión del dominio de calorías.
11. **RNF-E11 (Red local y HTTPS):** el servidor escucha en `0.0.0.0:5000` (HTTP) y `0.0.0.0:5443`
    (HTTPS) e imprime las IP/URL al arrancar. Requiere abrir ambos puertos en el Firewall de Windows.
    El certificado es de una **CA local** y cubre `localhost`, `127.0.0.1`, `::1`, el nombre de la PC
    y la IP de LAN. Para cámara y PWA en Android/iOS hay que instalar `ca.crt` una vez.
    Si cambia la IP se **regenera solo el certificado del servidor** y se conserva la CA, para no
    invalidar los certificados ya instalados ni la CA incluida en la APK.
12. **RNF-E12 (Base vacía):** al primer arranque `ef_usuarios`, `ef_estudiantes`, `ef_sesiones`,
    `ef_asistencias`, `ef_avisos`, `ef_pagos`, `ef_sedes` y `ef_categorias` están en **0 filas**.
    Nada se siembra automáticamente; el setup crea solo lo mínimo para operar.
13. **RNF-E13 (Respaldo):** el administrador descarga una copia consistente de `data/app.db` desde
    `/escuela/respaldo` (snapshot con la API de backup, válido con el servidor en marcha). Al
    arrancar se crea además un respaldo diario en `data/respaldos/` con rotación de 10 archivos;
    la copia manual con el servidor detenido también es válida.
14. **RNF-E14 (APK):** `minSdkVersion 24`, `targetSdkVersion 34`, firma v2/v3 con el keystore
    `android/keystore/escuela.jks`. La APK pesa < 1 MB, incluye `res/raw/ca_escuela.crt` y no
    necesita Gradle: se compila con las Build-Tools del SDK. Los datos nunca se guardan en el
    celular (solo la URL del servidor y los hosts cuyo certificado se aceptó).

---

## 6. Reglas de Negocio Inviolables (RN-E)

| Código | Regla | Dónde se aplica |
| :--- | :--- | :--- |
| **RN-E01** | Un alumno solo puede registrarse en la sesión de **su sede y su categoría**, y debe estar `ACTIVO`. | `escuela_service.registrar_asistencia` |
| **RN-E02** | Una asistencia es **única por sesión y alumno**: el segundo intento se rechaza. | Servicio + `UNIQUE(sesion_id, estudiante_id)` |
| **RN-E03** | **QR y marca manual son equivalentes**: ambos cuentan como asistencia completa y difieren solo en el método registrado. | Servicio + `CHECK (metodo IN ('QR','MANUAL'))` |
| **RN-E04** | Un aviso es **único por sesión y alumno**; generarlo dos veces no duplica ni reenvía. | `INSERT OR IGNORE` + `UNIQUE(sesion_id, estudiante_id)` |
| **RN-E05** | **0 asistencias en el mes = 0 Bs.** **1 o más asistencias = tarifa completa** de la categoría. No hay cobro proporcional. | `escuela_service.calcular_cobro` |
| **RN-E06** | Un alumno **becado no paga** (0 Bs), aunque haya asistido. | `escuela_service.calcular_cobro` |
| **RN-E07** | Solo se puede marcar **pagado/pendiente** cuando hay monto a cobrar (`monto > 0`). Sin asistencia o con beca, el cobro es `NO_APLICA`. | `escuela_service.marcar_pago` |

### 6.1 Reglas confirmadas pero fuera del MVP
Documentadas para no perderlas; **no** están implementadas y no deben presentarse como hechas:

- **RN-E08:** la **tardanza** cuenta como asistencia completa (equivalente a RN-E03 en el registro).
- **RN-E09:** cada alumno tiene **3 faltas recuperables por mes**.
- **RN-E10:** a la **cuarta falta** no se recupera, se avisa igual, **no cambia el cobro** y se
  **escala al director**.
- **RN-E11:** el **director aprueba** becas, sanciones, cambios de horario, cuarta falta y creación de
  sesiones de recuperación. Sin aprobación, la acción queda bloqueada.
- **RN-E12:** el cobro es **por alumno** y la tarifa **varía por categoría**
  (referencia: sub-8 400 Bs, sub-15 500 Bs, sub-18 600 Bs; monto general de referencia 500 Bs).

### 6.2 Validaciones de formato

| Dato | Formato / límite |
| :--- | :--- |
| `fecha` | `AAAA-MM-DD` |
| `hora` | `HH:MM` |
| `periodo` | `AAAA-MM` (mes 01–12) |
| `entrenador` | Texto, mínimo 3 caracteres |
| `nombre` del alumno | Texto, mínimo 3 caracteres |
| `sede_id` / `categoria_id` | Entero existente en el catálogo |
| `metodo` | `QR` o `MANUAL` |
| `estado` de pago | `PAGADO` o `PENDIENTE` |
| `usuario` | 3–30 caracteres: minúsculas, números, `.`, `-` o `_` |
| `clave` | Mínimo 6 caracteres, máximo 128 |
| `precio_mensual` | Número mayor que 0 |

---

## 7. Modelo de Datos (SQLite, migraciones 004 y 005)

```
ef_sedes 1──N ef_estudiantes N──1 ef_categorias
ef_sedes 1──N ef_sesiones   N──1 ef_categorias
ef_sesiones 1──N ef_asistencias N──1 ef_estudiantes
ef_sesiones 1──N ef_avisos      N──1 ef_estudiantes
ef_estudiantes 1──N ef_pagos
ef_estudiantes 1──N ef_usuarios   (0..1 por usuario ALUMNO)
```

### 7.1 `ef_sedes`
| Campo | Tipo | Restricción |
| :--- | :---: | :--- |
| `id` | int | PK, autoincremental |
| `nombre` | text | NOT NULL, UNIQUE |

### 7.2 `ef_categorias`
| Campo | Tipo | Restricción |
| :--- | :---: | :--- |
| `id` | int | PK, autoincremental |
| `nombre` | text | NOT NULL, UNIQUE |
| `precio_mensual` | real | NOT NULL, `CHECK > 0` |

### 7.3 `ef_estudiantes`
| Campo | Tipo | Restricción |
| :--- | :---: | :--- |
| `id` | int | PK, autoincremental |
| `nombre` | text | NOT NULL |
| `categoria_id` | int | NOT NULL, FK → `ef_categorias.id` |
| `sede_id` | int | NOT NULL, FK → `ef_sedes.id` |
| `qr_token` | text | NOT NULL, UNIQUE |
| `becado` | int | NOT NULL, default 0, `CHECK IN (0,1)` |
| `estado` | text | NOT NULL, default `ACTIVO`, `CHECK IN ('ACTIVO','INACTIVO')` |
| `fecha_registro` | text | NOT NULL |

### 7.4 `ef_sesiones`
| Campo | Tipo | Restricción |
| :--- | :---: | :--- |
| `id` | int | PK, autoincremental |
| `sede_id` | int | NOT NULL, FK → `ef_sedes.id` |
| `categoria_id` | int | NOT NULL, FK → `ef_categorias.id` |
| `fecha` | text | NOT NULL |
| `hora` | text | NOT NULL |
| `entrenador` | text | NOT NULL |
| `creada_en` | text | NOT NULL |
| — | — | `UNIQUE(sede_id, categoria_id, fecha, hora)` |

### 7.5 `ef_asistencias`
| Campo | Tipo | Restricción |
| :--- | :---: | :--- |
| `id` | int | PK, autoincremental |
| `sesion_id` | int | NOT NULL, FK → `ef_sesiones.id` |
| `estudiante_id` | int | NOT NULL, FK → `ef_estudiantes.id` |
| `metodo` | text | NOT NULL, default `QR`, `CHECK IN ('QR','MANUAL')` |
| `registrada_en` | text | NOT NULL |
| — | — | `UNIQUE(sesion_id, estudiante_id)` |

### 7.6 `ef_avisos`
| Campo | Tipo | Restricción |
| :--- | :---: | :--- |
| `id` | int | PK, autoincremental |
| `sesion_id` | int | NOT NULL, FK → `ef_sesiones.id` |
| `estudiante_id` | int | NOT NULL, FK → `ef_estudiantes.id` |
| `estado` | text | NOT NULL, default `PENDIENTE`, `CHECK IN ('PENDIENTE','ENVIADA')` |
| `creada_en` | text | NOT NULL |
| `enviada_en` | text | NULL |
| — | — | `UNIQUE(sesion_id, estudiante_id)` |

### 7.7 `ef_pagos`
| Campo | Tipo | Restricción |
| :--- | :---: | :--- |
| `id` | int | PK, autoincremental |
| `estudiante_id` | int | NOT NULL, FK → `ef_estudiantes.id` |
| `periodo` | text | NOT NULL (`AAAA-MM`) |
| `monto` | real | NOT NULL, `CHECK >= 0` |
| `estado` | text | NOT NULL, default `PENDIENTE`, `CHECK IN ('PAGADO','PENDIENTE')` |
| `fecha_pago` | text | NULL |
| — | — | `UNIQUE(estudiante_id, periodo)` |

### 7.8 `ef_usuarios` (migración 005)
| Campo | Tipo | Restricción |
| :--- | :---: | :--- |
| `id` | int | PK, autoincremental |
| `usuario` | text | NOT NULL, UNIQUE (se guarda en minúsculas) |
| `nombre` | text | NOT NULL |
| `password_hash` | text | NOT NULL (`generate_password_hash`) |
| `rol` | text | NOT NULL, `CHECK IN ('ADMIN','ENTRENADOR','ALUMNO')` |
| `estudiante_id` | int | NULL, FK → `ef_estudiantes.id` (obligatorio en la práctica para `ALUMNO`) |
| `activo` | int | NOT NULL, default 1 |
| `fecha_creacion` | text | NOT NULL |

---

## 8. Contrato de la API (`/api/escuela`)

| Método | Ruta | Función | Roles |
| :--- | :--- | :--- | :--- |
| GET | `/escuela` | Panel compartido; redirige a login sin sesión | ADMIN, ENTRENADOR, ALUMNO |
| GET/POST | `/escuela/setup` | Primer arranque: crea el admin y el catálogo mínimo (solo con base vacía) | público |
| GET/POST | `/escuela/login` | Login contra `ef_usuarios` (sin credenciales demo) | público |
| GET/POST | `/escuela/logout` | Cierra solo la sesión de la escuela | autenticado |
| GET | `/contexto` | Sedes, categorías, estudiantes, sesiones de hoy y KPIs | ADMIN, ENTRENADOR |
| GET | `/mi?periodo=AAAA-MM` | QR, historial, faltas y cobro del propio alumno | ALUMNO |
| GET | `/sesiones?fecha=AAAA-MM-DD` | Listar sesiones (opcionalmente por fecha) | ADMIN, ENTRENADOR |
| POST | `/sesiones` | Abrir o reutilizar una sesión | ADMIN, ENTRENADOR |
| GET | `/sesiones/<id>` | Detalle: presentes, ausentes, avisos y estadísticas | ADMIN, ENTRENADOR |
| POST | `/sesiones/<id>/asistencia` | Registrar asistencia (`qr_token` o `estudiante_id` + `metodo`) | ADMIN, ENTRENADOR |
| POST | `/sesiones/<id>/avisos` | Generar avisos de todos los ausentes | ADMIN, ENTRENADOR |
| GET | `/avisos?estado=PENDIENTE` | Listar avisos con mensaje redactado | ADMIN, ENTRENADOR |
| POST | `/avisos/<id>/enviado` | Marcar el aviso como enviado | **solo ADMIN** |
| GET | `/cobros?periodo=AAAA-MM` | Cobros por alumno + resumen del periodo | **solo ADMIN** |
| POST | `/cobros` | Marcar `PAGADO` o `PENDIENTE` | **solo ADMIN** |
| GET | `/resumen` | KPIs del día y del periodo | ADMIN, ENTRENADOR |
| GET | `/estudiantes/<id>/qr.svg` | QR del alumno en SVG | ADMIN, ENTRENADOR; ALUMNO solo el suyo |
| GET | `/estudiantes` | Listar alumnos activos | **solo ADMIN** |
| POST | `/estudiantes` | Alta manual de alumno y cuenta opcional (`usuario`, `clave`) | **solo ADMIN** |
| POST | `/estudiantes/<id>/cuenta` | Crear cuenta de acceso para un alumno existente | **solo ADMIN** |
| POST | `/estudiantes/<id>/baja` | Baja lógica (`INACTIVO`), conserva historial | **solo ADMIN** |
| GET | `/usuarios` | Listar cuentas (sin hashes) | **solo ADMIN** |
| POST | `/usuarios` | Crear cuenta `ADMIN`/`ENTRENADOR` | **solo ADMIN** |
| POST | `/usuarios/<usuario>/clave` | Cambiar contraseña de una cuenta | **solo ADMIN** |
| POST | `/sedes` | Agregar una sede | **solo ADMIN** |
| POST | `/categorias` | Agregar categoría con tarifa | **solo ADMIN** |
| GET | `/escuela/respaldo` | Descargar copia consistente de `data/app.db` | **solo ADMIN** |
| GET | `/ca.crt` | Descargar la CA local para instalar en celulares | público (solo certificado) |

**Formato de error:** `{"error": "mensaje legible"}` con HTTP **400** (regla de negocio), **401**
(sin sesión), **403** (rol sin permiso) o **404** (recurso inexistente).
**Páginas sin sesión:** `302` hacia `/escuela/login`. La demo aislada `?modo=local` no pide login.

---

## 9. Criterios de Aceptación Verificables (Dado · Cuando · Entonces)

### CA-E01: Registro por QR
- **Dado** un alumno activo con token `EF-XXXX` y una sesión de su sede y categoría,
- **Cuando** el entrenador escanea o escribe el token,
- **Entonces** el sistema registra la asistencia con `metodo = QR` y el alumno desaparece de la lista de ausentes.

### CA-E02: Registro manual equivalente
- **Dado** el mismo alumno y la misma sesión,
- **Cuando** el entrenador lo marca desde la lista de ausentes,
- **Entonces** la asistencia se registra igual que por QR, con `metodo = MANUAL`, y cuenta para el cobro.

### CA-E03: Rechazo de duplicado
- **Dado** un alumno ya registrado en la sesión,
- **Cuando** se intenta registrar otra vez (por QR o manual),
- **Entonces** el sistema responde 400 con «ya está registrado» y no crea un segundo registro.

### CA-E04: Rechazo de alumno ajeno a la sesión
- **Dado** un alumno de otra categoría u otra sede,
- **Cuando** se intenta registrar en la sesión,
- **Entonces** el sistema responde 400 con «no pertenece a la sede y categoría» y no registra nada.

### CA-E05: Generación idempotente de avisos
- **Dado** una sesión con ausentes,
- **Cuando** se generan los avisos dos veces,
- **Entonces** la primera vez crea un aviso `PENDIENTE` por ausente y la segunda informa
  `creados = 0` sin duplicar.

### CA-E06: Aviso enviado
- **Dado** un aviso pendiente con el mensaje redactado,
- **Cuando** el administrador lo marca como enviado,
- **Entonces** pasa a `ENVIADA`, guarda `enviada_en` y deja de aparecer entre los pendientes.

### CA-E07: Cobro sin asistencias
- **Dado** un alumno activo sin ninguna asistencia en el periodo,
- **Cuando** se calcula su cobro,
- **Entonces** el monto es **0 Bs**, el motivo es `SIN_ASISTENCIA` y el estado es `NO_APLICA`.

### CA-E08: Cobro con una o más asistencias
- **Dado** un alumno de sub-15 (500 Bs) con **una** asistencia en el mes,
- **Cuando** se calcula su cobro,
- **Entonces** el monto es **500 Bs** (tarifa completa), el motivo es `ASISTENCIA` y el estado
  inicial es `PENDIENTE`.

### CA-E09: Alumno becado
- **Dado** un alumno con `becado = 1` y asistencias registradas,
- **Cuando** se calcula su cobro,
- **Entonces** el monto es **0 Bs** y el motivo es `BECA`.

### CA-E10: Marcar pagado y volver a pendiente
- **Dado** un cobro con monto mayor a 0,
- **Cuando** el administrador lo marca `PAGADO`,
- **Entonces** se guarda `fecha_pago` y el resumen suma el monto a «cobrado»;
  si luego lo marca `PENDIENTE`, se limpia `fecha_pago` y vuelve a «pendiente».

### CA-E11: No se marca pago sin monto
- **Dado** un alumno sin asistencias o becado,
- **Cuando** se intenta marcar `PAGADO`,
- **Entonces** el sistema responde 400 con «No hay monto a cobrar» y no crea un pago.

### CA-E12: Validación de periodo
- **Dado** un periodo con formato inválido (por ejemplo `2026-13`),
- **Cuando** se consultan los cobros,
- **Entonces** el sistema responde 400 indicando el formato `AAAA-MM`.

### CA-E13: QR descargable
- **Dado** un alumno registrado,
- **Cuando** se solicita `/api/escuela/estudiantes/<id>/qr.svg`,
- **Entonces** el sistema devuelve un SVG válido (`image/svg+xml`) con su token.

### CA-E14: Operación sin conexión
- **Dado** un entrenador sin internet en la sede,
- **Cuando** registra una asistencia,
- **Entonces** el navegador la guarda en `localStorage` y la envía sola al recuperar la conexión,
  sin perder el registro.

### CA-E15: Migración idempotente
- **Dado** una base nueva o existente,
- **Cuando** arranca la aplicación,
- **Entonces** las migraciones pendientes se aplican una sola vez y quedan registradas en
  `schema_migrations`.

### CA-E16: Modo app con datos locales
- **Dado** el panel abierto con `?modo=local` o desde la PWA instalada,
- **Cuando** se registra asistencia, se generan avisos o se marca un pago,
- **Entonces** las mismas reglas RN-E01–RN-E07 se ejecutan en el dispositivo sobre IndexedDB, sin
  llamadas a `/api/escuela`, y «Reiniciar demo» reconstruye el estado inicial.

### CA-E17: Login por rol
- **Dado** un usuario creado en el sistema (`ADMIN`, `ENTRENADOR` o `ALUMNO`),
- **Cuando** ingresa sus credenciales en `/escuela/login`,
- **Entonces** se abre una sesión con su rol y nombre, y es redirigido a `/escuela`.
- **Dado** credenciales incorrectas, **Cuando** intenta entrar, **Entonces** recibe **401** con el
  formulario y un mensaje de error, sin crear sesión.

### CA-E18: Entrenador sin acceso a cobros
- **Dado** una sesión con rol `ENTRENADOR`,
- **Cuando** abre `/escuela` o llama a `/api/escuela/cobros`,
- **Entonces** el panel no muestra la pestaña ni el bloque de cobros, la API responde **403** y
  tampoco puede marcar avisos como enviados.

### CA-E19: Alumno ve solo su registro
- **Dado** una sesión con rol `ALUMNO` asociada a un estudiante,
- **Cuando** abre `/escuela` y `/api/escuela/mi`,
- **Entonces** ve su QR, sus asistencias/faltas y su cobro del mes; `/api/escuela/contexto` y el QR
  de otro alumno responden **403**.

### CA-E20: Datos compartidos en la red local
- **Dado** el servidor corriendo en la PC (`0.0.0.0:5000`) y dos dispositivos en la misma red
  (cualquier WiFi, hotspot o cable),
- **Cuando** el entrenador registra una asistencia en su celular,
- **Entonces** la administradora la ve al recargar el panel en su laptop, sin copiar datos ni
  sincronizar archivos, porque ambos leen la misma SQLite.

### CA-E21: Base vacía y primer administrador
- **Dado** un archivo `data/app.db` recién creado (todas las tablas `ef_*` en 0 filas),
- **Cuando** se abre `/escuela/setup` y se envían nombre, usuario y contraseña válidos,
- **Entonces** se crea el `ADMIN`, se crean 2 sedes y 3 categorías mínimas, y la sesión queda iniciada.
- **Dado** que ya existe una cuenta, **Cuando** se vuelve a abrir `/escuela/setup`, **Entonces** redirige
  a `/escuela/login` sin crear otro administrador.

### CA-E22: Alta de alumno con cuenta opcional
- **Dado** un administrador autenticado y un catálogo con sede/categoría,
- **Cuando** registra un alumno sin usuario, **Entonces** el alumno queda `ACTIVO` con un QR único y sin cuenta.
- **Cuando** registra un alumno con usuario y contraseña, **Entonces** además se crea una cuenta `ALUMNO`
  vinculada a ese alumno y puede iniciar sesión.

### CA-E23: HTTPS y cámara/PWA
- **Dado** el servidor arrancado en la PC,
- **Cuando** un celular abre `https://IP_DE_LA_PC:5443/escuela` con la CA local instalada,
- **Entonces** la conexión es de confianza, el navegador permite instalar la PWA y usar la cámara.
- **Cuando** se descarga `https://IP_DE_LA_PC:5443/ca.crt`, **Entonces** se obtiene la CA para instalar.

### CA-E24: Respaldo y permisos de altas
- **Dado** un administrador autenticado, **Cuando** abre `/escuela/respaldo`, **Entonces** descarga una
  copia `.db` consistente (válida aunque el servidor esté registrando asistencias).
- **Dado** un servidor que arranca con cuentas creadas, **Cuando** inicia, **Entonces** guarda una
  copia diaria en `data/respaldos/` sin duplicar la del mismo día.
- **Dado** un entrenador, **Cuando** intenta crear alumnos, cuentas, sedes o categorías, **Entonces**
  recibe **403** y el panel no muestra la pestaña **Altas y cuentas**.

### CA-E25: APK de Android
- **Dado** un celular Android con `EscuelaUAB.apk` instalada y conectado a la misma red que la PC
  (cualquier WiFi, hotspot o cable),
- **Cuando** se configura `https://IP_DE_LA_PC:5443/escuela` y se abre la app,
- **Entonces** el panel carga sin instalar la CA por separado (va incluida en la APK) y el login funciona.
- **Cuando** el entrenador toca **Escanear QR**, **Entonces** Android pide permiso de cámara una vez y,
  si el WebView soporta `BarcodeDetector`, el escaneo funciona; si no, queda la marca manual.
- **Cuando** el administrador descarga el respaldo desde la APK, **Entonces** el archivo queda en
  `Descargas/EscuelaUAB/` con la sesión (cookie) incluida.
- **Cuando** la IP de la PC cambia, **Entonces** basta **⋮ → Cambiar servidor**; no hace falta reinstalar
  la APK ni la CA (misma CA, certificado del servidor regenerado).

---

## 10. Trazabilidad Regla ↔ Prueba

Suite: `tests/test_escuela.py` (**31 pruebas**), `tests/test_certificados.py` (**4 pruebas**),
`tests/test_app.py` (**53 pruebas**, incluidas las 2 de detección de red y las 9 de regresión) y
suite completa (**88 pruebas**).

| Regla / criterio | Prueba |
| :--- | :--- |
| CA-E01 | `test_registra_asistencia_con_qr` |
| CA-E02 | `test_marca_manual_equivale_a_qr` |
| CA-E03 | `test_rechaza_doble_registro` |
| CA-E04 | `test_rechaza_estudiante_de_otra_categoria` |
| CA-E05 / CA-E06 | `test_generar_avisos_es_idempotente` |
| CA-E07 | `test_cobro_cero_sin_asistencias` |
| CA-E08 | `test_cobro_precio_completo_con_una_asistencia` |
| CA-E09 | `test_becado_no_paga` |
| CA-E10 | `test_marcar_pagado_y_pendiente` |
| CA-E11 | `test_no_marca_pago_sin_monto` |
| CA-E12 | `test_periodo_invalido` |
| CA-E13 | `test_generar_qr_svg`, `test_api_contexto_y_qr` |
| CA-E14 | Prueba manual en navegador (no automatizable sin navegador) |
| CA-E15 | `test_tc29_migraciones_versionadas_e_idempotentes` |
| CA-E16 | `test_local.js` (Node + IndexedDB simulada): contexto, duplicados, avisos, cobros y QR local |
| CA-E17 | `test_login_con_roles`, `test_sin_sesion_protege_panel_y_api` |
| CA-E18 | `test_entrenador_no_puede_cobrar_ni_marcar_avisos` |
| CA-E19 | `test_alumno_ve_solo_su_registro` |
| CA-E20 | Verificación HTTP real en LAN (manual) + `test_api_registrar_asistencia` |
| CA-E21 | `test_setup_crea_admin_y_catalogo_en_base_vacia` |
| CA-E22 | `test_crear_alumno_con_y_sin_cuenta`, `test_api_altas_y_cuentas_admin` |
| CA-E23 | Verificación HTTP/HTTPS real (manual) + `/ca.crt` |
| CA-E24 | `test_api_respaldo_descarga_copia_valida`, `test_respaldo_consistente_y_automatico`, `test_entrenador_no_puede_gestionar_altas` |
| CA-E25 | Verificación manual con `apksigner verify` + instalación en emulador/celular (APK WebView) |

---

## 11. Supuestos, Riesgos y Aspectos [POR DEFINIR]

### Definido
- Alcance MVP de **3 funciones** y separación estricta respecto del dominio de calorías.
- Tarifas de referencia por categoría (400 / 500 / 600 Bs) y monto general de referencia 500 Bs.
- Cobro mensual por alumno, sin prorrateo: 0 asistencias = 0 Bs; 1 o más = tarifa completa.
- Beca respetada en el cálculo; tardanza equivalente a asistencia (RN-E03).
- QR generado en el servidor y escaneo con `BarcodeDetector` en el navegador, con fallback manual.
- Cola local para operar sin internet.
- **Arquitectura compartida:** una sola SQLite en la PC, servidor Flask en `0.0.0.0:5000` (HTTP) y
  `0.0.0.0:5443` (HTTPS), con acceso desde laptop y celulares de la **misma red**: cualquier WiFi,
  hotspot o cable. El certificado cubre todas las IPs de la PC y se regenera solo al cambiar de red
  (la CA se conserva).
- **Roles implementados:** `ADMIN`, `ENTRENADOR` y `ALUMNO`, con cuentas creadas por el administrador
  y autorización en servidor.
- **Base vacía:** sin usuarios, alumnos, sesiones ni pagos sembrados; `/escuela/setup` crea el primer
  administrador y el catálogo mínimo.
- **Altas y cuentas:** alumnos manuales con QR, cuenta opcional del alumno, cuentas de personal,
  cambio de contraseña, sedes/categorías y baja lógica.
- **HTTPS local:** CA propia y certificado con la IP de LAN; `/ca.crt` para instalar en los celulares.
  La CA se conserva al cambiar de IP (solo se regenera el certificado del servidor).
- **APK de Android:** cliente WebView firmado en `android/dist/EscuelaUAB.apk`, con URL configurable,
  cámara, descargas y la CA local incluida. Se recompila con `android/build_apk.ps1` (sin Gradle).
- **Respaldo:** descarga consistente desde el panel y copia diaria automática en `data/respaldos/`.
- **Vista del alumno:** solo lectura de su QR, faltas y cobro.
- Demo local aislada (`?modo=local`) con IndexedDB, conservada para usar sin red.

### [POR DEFINIR]
1. **Impresión del QR**: hoy se muestra y se descarga; el diseño y formato de impresión no están definidos.
2. **Comprobante de pago numerado** (formato, serie, datos obligatorios).
3. **Recuperaciones y límite de 3 faltas**: flujo, cupos y cómo se crea la sesión de recuperación.
4. **Cuarta falta**: qué pasa mientras el director no la aprueba y cómo se registra la sanción.
5. **Aprobaciones del director**: dónde se registran y cómo se bloquea la acción sin aprobación.
6. **Justificaciones de falta**: tipos válidos (médico, viaje, etc.) y si afectan el cobro.
7. **Reemplazo del director** cuando no está disponible.
8. **Acceso del padre**: si tendrá portal propio o solo mensajes.
9. **Mora y redondeo**: política de pagos atrasados y precisión del monto.
10. **Desglose real de las 24–26 h** (bitácora de `docs/VALIDACION_HORAS.md` en curso).
11. **Firma y publicación de la APK**: hoy se instala manualmente (APK fuera de Google Play); la
    distribución y el resguardo de `escuela.jks` quedan a cargo de la escuela.
12. **Acceso desde internet**: hoy solo LAN. Para fuera de la escuela hace falta túnel HTTPS u hosting.
13. **Respaldo programado cada hora**: hoy hay copia diaria al arrancar y descarga manual; una tarea
    programada de Windows queda `[POR DEFINIR]`.

### Riesgos
| Riesgo | Impacto | Mitigación |
| :--- | :--- | :--- |
| `BarcodeDetector` no existe en el navegador/WebView del entrenador | No puede escanear | Marca manual desde la lista de ausentes o código escrito a mano |
| CA local no instalada en el celular | Advertencia de certificado; PWA/cámara bloqueadas | La APK ya incluye la CA; para el navegador, instalar `ca.crt` una vez; HTTP 5000 sigue disponible |
| La IP de la PC cambia | La URL guardada deja de funcionar | El servidor conserva la CA y regenera el certificado; actualizar la dirección en **⋮ → Cambiar servidor** |
| La PC servidor se apaga o el Firewall bloquea los puertos | Los celulares no conectan | Dejar la PC encendida y abrir 5000 y 5443; la consola imprime las IP correctas |
| Un solo archivo SQLite sin respaldo externo | Pérdida de asistencias y pagos | Copia diaria automática en `data/respaldos/`, descarga desde el panel y copia semanal fuera de la PC |
| Datos de alumnos reales en la demo local | Privacidad | La demo local usa nombres ficticios; no publicar `data/app.db` ni `src/certs/*.key` |
| No se demuestra el ahorro de horas | Se cae el argumento del proyecto | Medir con la bitácora antes de afirmar la reducción |
