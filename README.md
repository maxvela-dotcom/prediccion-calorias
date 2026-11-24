# Calorías en Rutina · Proyecto UAB (Flask + SQLite)

Aplicación web local para **predecir las calorías quemadas en una rutina** de ejercicio.
Incluye **registro e inicio de sesión**: la plataforma interna (dashboard, historial y perfil) solo es accesible después de autenticarse.

Proyecto construido sobre el **Starter Kit UAB** bajo el patrón **Monolito Modular por Capas**
(`Controller -> Service -> Repository -> Model`), con persistencia local en **SQLite**.

---

## ⚽ Módulo Escuela de Fútbol (entrega actual)

Sobre el dominio de ejemplo de calorías se construyó la app real **Escuela de Fútbol**,
aislada en `/escuela`, `/api/escuela` y tablas `ef_*`:

- **Arranque rápido (Windows):** doble clic en `iniciar_escuela.bat`.
- **Preparar la red (una sola vez, como administrador):** doble clic en `preparar_red.bat`
  (habilita los puertos 5000 y 5443 en el Firewall de Windows para **cualquier red**: WiFi de la
  escuela, otra WiFi, hotspot o cable).
- **Primer arranque:** abre `http://127.0.0.1:5000/escuela/setup` y crea el administrador.
  La base empieza **completamente vacía** (sin alumnos, sesiones, pagos ni usuarios demo).
- **Celulares (navegador):** `https://IP_DE_LA_PC:5443/escuela`; instala antes la CA local desde
  `https://IP_DE_LA_PC:5443/ca.crt` para habilitar cámara y PWA.
- **APK de Android:** `android/dist/EscuelaUAB.apk` (cliente WebView; los datos siguen en la PC).
  Instálala en el celular y configura la IP desde el menú **⋮ → Cambiar servidor**.
  Para recompilar: `powershell -ExecutionPolicy Bypass -File android\build_apk.ps1`.
- **Guía completa:** [`docs/GUIA_DEMO_ESCUELA.md`](docs/GUIA_DEMO_ESCUELA.md) ·
  **Contrato:** [`docs/SPEC_ESCUELA.md`](docs/SPEC_ESCUELA.md).

> La PC es el servidor único: todos los dispositivos de la **misma red** (cualquier WiFi, hotspot o
> cable) leen y escriben la misma SQLite (`data/app.db`). El respaldo se descarga desde el panel y
> además se guarda una copia diaria automática en `data/respaldos/`.

---

## ✨ Funcionalidades
- Registro de cuenta con contraseña segura (hash + política mínima) y validación **CSRF** en formularios.
- **Verificación de correo** y **recuperación de contraseña** con tokens de un solo uso. El envío por **SMTP es opcional**: si no hay credenciales, el enlace se imprime en consola.
- Inicio/cierre de sesión y protección de `/dashboard`, `/api/calorias`, `/api/perfil` y `/api/usuarios`.
- **Perfil ampliado** con `peso_preferido_kg`, `altura_preferida_cm`, `edad`, `sexo` y `fc_reposo` (API `/api/perfil`).
- **Catálogo MET versionado** (`/api/met-catalogo`) con 15 actividades, versión, fuente y estado de validación.
- Predicción de calorías con **regresión lineal múltiple** como método principal:
  - **Regresión:** `Ŷ = β0 + β1X1 + β2X2 + β3X3 + β4X4`, con `β = (XᵀX)⁻¹ XᵀY` entrenado desde `data/dataset_calorias.csv` (80 filas ficticias y anonimizadas; X1 peso, X2 altura, X3 edad, X4 minutos).
  - **Respaldo MET:** `calorias = MET × peso_kg × (duracion_min / 60)`.
  - **Respaldo Keytel:** si hay FC promedio + edad + sexo, usa la ecuación de Keytel et al. (2005).
  - Cada predicción guarda un `modelo_snapshot` con los `β` usados para reconstruir su desglose aunque cambie el CSV.
- **Análisis técnico visible** en `/dashboard`: dataset y estadísticos, vistas previas de `X` (columna de unos), `Xᵀ`, `Y`, `XᵀX`, `XᵀY` y `β` con dimensiones, ecuación e interpretación de cada coeficiente, MAE/RMSE/R² y 3 gráficas (Chart.js servido localmente, sin Internet).
- Historial personal **paginado** con filtros por actividad/texto, total de registros, calorías acumuladas y **exportación CSV**.
- Seguridad: **CSRF** en formularios y APIs JSON (`X-CSRF-Token`), **rate limiting pluggable** (memoria por defecto, Redis opcional con fallback) y cookies `HttpOnly`/`SameSite=Lax`.
- Persistencia local SQLite (`data/app.db`) con **migraciones versionadas** (`schema_migrations`) para usuarios, predicciones y módulo base.

---

## 📁 Estructura del Proyecto

```text
starter-kit-uab/
├── README.md
├── AGENT_RULES.md
├── requirements.txt
├── .gitignore
├── .env.example
├── iniciar_escuela.bat / .ps1  # Arranque de la app compartida (Windows)
├── preparar_red.bat / .ps1     # Habilita 5000/5443 en el Firewall (admin)
├── instalar_ca_windows.bat / .ps1  # Confía en la CA local en Chrome/Edge de la PC
├── android/                    # Cliente Android (WebView) + build_apk.ps1
│   ├── AndroidManifest.xml
│   ├── java/bo/uab/escuela/MainActivity.java
│   ├── res/                    # Icono, CA local y configuración de red
│   ├── keystore/escuela.jks    # Firma de la APK (guardar, no publicar)
│   └── dist/EscuelaUAB.apk     # APK firmada lista para instalar
├── data/                       # Base SQLite local + dataset_calorias.csv (entrenamiento)
├── docs/
│   ├── IDEA.md                   # Problema, beneficiario y matriz de claridad
│   ├── SPEC.md                   # Contrato del MVP: reglas, modelos y criterios
│   ├── SPEC_ESCUELA.md           # Contrato del módulo Escuela de Fútbol
│   ├── GUIA_DEMO_ESCUELA.md      # Uso, HTTPS, CA, respaldo y límites
│   ├── ARCHITECTURE.md           # Monolito Modular por Capas (ADR-001/002)
│   ├── DATABASE.md               # Esquema SQLite, diccionario y restricciones
│   ├── API.md                    # Rutas web y contratos REST
│   ├── TECH_STACK.md
│   ├── TESTING.md
│   └── EVALUATION.md
├── src/
│   ├── main.py                   # Rutas web, sesión, CSRF, perfil, arranque HTTP/HTTPS
│   ├── certificados.py           # CA local y certificado HTTPS con la IP de la LAN
│   ├── security.py               # Rate limiting pluggable (memoria/Redis), CSRF y tokens
│   ├── notificaciones.py         # SMTP opcional con fallback a consola
│   ├── database.py               # Conexión, migraciones versionadas y respaldos
│   ├── templates/
│   │   ├── escuela.html          # Panel ADMIN/ENTRENADOR + pestaña Altas y cuentas
│   │   ├── escuela_login.html    # Login de la escuela
│   │   ├── escuela_setup.html    # Primer arranque (crea el administrador)
│   │   ├── escuela_alumno.html   # Vista de solo lectura del alumno
│   │   ├── login.html            # Inicio de sesión del dominio de calorías
│   │   ├── register.html         # Crear cuenta (público)
│   │   ├── recuperar.html        # Solicitud de recuperación (público)
│   │   ├── reset.html            # Nueva contraseña con token (público)
│   │   ├── mensaje.html          # Resultado de verificación/reset
│   │   ├── dashboard.html        # Plataforma interna + análisis técnico y gráficas (protegida)
│   │   └── index.html            # Dashboard base del starter-kit
│   ├── static/
│   │   └── chart.umd.min.js      # Chart.js local (funciona sin conexión)
│   └── modulos/
│       ├── escuela/              # Modelo/Repo/Service/Controller + QR del módulo Escuela
│       ├── usuarios/             # Modelo/Repo/Service/Controller de usuarios y auth
│       ├── prediccion_calorias/  # Modelo/Repo/Service/Controller + catálogo MET + regresion_lineal.py
│       └── gestion_mvp/          # Módulo base conservado (/api/mvp)
└── tests/
    ├── test_app.py               # 53 pruebas de calorías, regresión, usuarios y Google Sign-In
    ├── test_escuela.py           # 31 pruebas del módulo Escuela
    └── test_certificados.py      # 4 pruebas de la CA local (reutilización, IPs)
```

---

## 🚀 Cómo Empezar a Trabajar (Los 3 Pasos Mágicos)

### Paso 1: Levantar el Entorno Virtual e Instalar Flask
Abre la terminal en la carpeta `starter-kit-uab` y ejecuta:

```bash
# En Windows (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# En Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### Paso 2: Levantar el Servidor Web Flask
Ejecuta el servidor de aplicaciones:

```bash
python src/main.py
```
> *El servidor inicia HTTP en `http://127.0.0.1:5000` y HTTPS en `https://IP_DE_LA_PC:5443`.
> La app de la escuela está en `/escuela` y la de calorías en `/login`.
> La base SQLite se crea automáticamente en `data/app.db`.*
>
> *En Windows también puedes usar `iniciar_escuela.bat` (doble clic), que verifica el entorno
> virtual, instala dependencias si faltan y arranca el servidor.*

---

### Paso 3: Ejecutar la Batería de Pruebas Automatizadas
Verifica que las **88 pruebas** (53 en `test_app.py` —incluye 2 de detección de red— + 31 de la
escuela + 4 de certificados) pasen en verde:

```bash
# Usando unittest nativo de Python:
python -m unittest discover -s tests

# O con pytest:
pytest tests/
```

> Las pruebas usan una base SQLite temporal por caso, por lo que no afectan tus datos locales.

---

## ☁️ Despliegue en Render.com

La SQLite se crea automáticamente al arrancar (`crear_app()` → `init_db()`), así que no hace falta subir `data/app.db`. El dataset `data/dataset_calorias.csv` sí va en el repositorio.

En el servicio Web de Render (**Runtime: Python**) configura:

- **Build Command**
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**
  ```bash
  gunicorn --chdir src main:app --bind 0.0.0.0:$PORT
  ```

Variables de entorno recomendadas en el dashboard de Render:

- `FLASK_SECRET_KEY` (obligatoria en producción; cambia la clave de desarrollo).
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` (usa la URL HTTPS de Render, p. ej. `https://<tu-servicio>.onrender.com/google/callback`). `GOOGLE_HD` queda vacío para aceptar cualquier cuenta.
- Opcionales: `SMTP_*`, `RATE_LIMIT_BACKEND`/`REDIS_URL`.

**Persistencia:** el sistema de archivos de Render es efímero. Si quieres conservar usuarios y predicciones entre reinicios, añade un **Persistent Disk** montado en `/opt/render/project/data` y define:

```bash
DATABASE_PATH=/opt/render/project/data/app.db
```

Así la base vive en el disco y `data/dataset_calorias.csv` sigue disponible dentro del repositorio.

---

## ⚙️ Configuración opcional (SMTP y Redis)

Copia `.env.example` a `.env` y ajusta solo lo que necesites:

- **Correo real:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` (y `SMTP_FROM`/`SMTP_USE_TLS`). Sin credenciales válidas, los enlaces de verificación/recuperación se imprimen en consola.
- **Rate limiting distribuido:** `RATE_LIMIT_BACKEND=redis` y `REDIS_URL=redis://...` (instala antes con `pip install redis`). Por defecto (`auto`/`memory`) usa memoria y cae a ella si Redis no responde.
- **Google Sign-In (opcional):** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` y `GOOGLE_REDIRECT_URI` (ej. `http://127.0.0.1:5000/google/callback`). Sin credenciales el botón se muestra desactivado con `[POR DEFINIR]`. `GOOGLE_HD` permite restringir a un dominio; vacío acepta cualquier cuenta.
- **Migraciones:** se aplican automáticamente al iniciar. Cada versión queda registrada en `schema_migrations`; son idempotentes y compatibles con bases anteriores.

---

## 🔐 Flujo de la Aplicación

1. **Visitante** → `/login` o `/registro` (rutas públicas, con CSRF). En `/login` aparece además **Continuar con Google**.
2. **Acceso** → con correo/contraseña (registro: nombre/correo/contraseña >=8 con letras y números, hash y verificación por SMTP o consola) **o** con Google (`/google/login` → `/google/callback`, con `state` anti-CSRF y verificación del ID token en el servidor). Si el correo de Google ya existe, se vincula conservando historial y contraseña; si es nuevo, se crea una cuenta GOOGLE con contraseña aleatoria desconocida.
3. **Dashboard protegido** (`/dashboard`) → requiere sesión. Muestra perfil, estado de verificación, catálogo MET versionado, formulario de predicción y el **análisis técnico de la regresión** con 3 gráficas.
4. **Predicción** → `POST /api/calorias` (sesión + `X-CSRF-Token`) aplica **regresión lineal múltiple** cuando hay peso, altura, edad y duración; si falta altura o edad, usa **Keytel** (FC/edad/sexo) o **MET** como respaldo. Guarda en SQLite junto con los `β` usados (`modelo_snapshot`), devuelve el **desglose del cálculo** y actualiza el historial paginado.
5. **Perfil** → `GET/POST /api/perfil` actualiza peso, altura, edad, sexo y FC de reposo; la altura del perfil se usa como X2 si el formulario no la especifica.
6. **Historial y papelera** → el dashboard permite **Ver cálculo** (`GET /api/calorias/<id>`) y **Borrar** (`DELETE /api/calorias/<id>`), que mueve el registro a la papelera. Desde allí se puede **restaurar**, **borrar definitivamente** o **vaciar la papelera**; todo con sesión + CSRF y solo sobre registros propios.
7. **Exportación** → `GET /api/calorias/export.csv` descarga el historial activo filtrado en CSV.
8. **Recuperación** → `/recuperar` genera un enlace (SMTP o consola) → `/reset/<token>` define nueva contraseña.
9. **Logout** → limpia sesión y bloquea nuevamente el acceso.

## 🔎 Endpoints principales
- Web: `GET|POST /registro`, `GET|POST /login`, `GET /google/login`, `GET /google/callback`, `GET /logout`, `GET /dashboard`
- Recuperación: `GET|POST /recuperar`, `GET|POST /reset/<token>`, `GET /verificar/<token>`
- Usuarios: `POST /api/usuarios` (público, con rate limit), `GET /api/usuarios` (sesión), `POST /api/usuarios/<id>/baja` (sesión + CSRF)
- CSRF: `GET /api/csrf-token`
- Calorías (sesión): `GET|POST /api/calorias` (`?q=`, `?actividad=`, `?page=`, `?per_page=`), `GET /api/calorias/analisis` (datos del modelo y gráficas), `GET /api/calorias/<id>` (desglose), `DELETE /api/calorias/<id>` (a papelera, con CSRF), `GET /api/calorias/papelera`, `POST /api/calorias/<id>/restaurar`, `DELETE /api/calorias/<id>/definitivo`, `DELETE /api/calorias/papelera`, `GET /api/calorias/export.csv`
- Perfil (sesión): `GET|POST|PUT /api/perfil`
- Catálogo: `GET /api/met-catalogo` (incluye `catalogo.version`, `fuente` y `revision`)
- Base starter-kit: `/api/mvp` y `/api/mvp/metricas`

## 📈 Regresión lineal y análisis técnico

El dataset `data/dataset_calorias.csv` tiene 80 filas anonimizadas con `X_1` peso (kg), `X_2` altura (cm), `X_3` edad (años), `X_4` minutos y `Y` calorías. `src/modulos/prediccion_calorias/regresion_lineal.py` construye `X` con una columna de unos y resuelve la ecuación normal de forma explícita con NumPy:

```text
β = (XᵀX)⁻¹ · XᵀY        X: 80×5   Xᵀ: 5×80   XᵀX: 5×5   XᵀY: 5×1   β: 5×1
Ŷ = β0 + β1X1 + β2X2 + β3X3 + β4X4
```

Métricas del dataset actual: **MAE 1.3155**, **RMSE 1.5224**, **R² 0.9999**. `/dashboard` muestra el dataset y sus estadísticos, las matrices con dimensiones, la interpretación de cada `β_i`, esas métricas y 3 gráficas: real vs predicho, residuos vs predicción e impacto de cada variable. `GET /api/calorias/analisis` expone toda esa información en JSON (requiere sesión). El desglose de cada predicción usa el `modelo_snapshot` guardado, por lo que los registros antiguos se explican con los coeficientes originales aunque se reentrene el modelo.

---

## 🧪 Pruebas
`tests/test_app.py` cubre (TC-01 a TC-51):
- Unitarias de las capas (Model/Repository/Service/Controller) del MVP base y usuarios.
- Predicción con **regresión lineal múltiple** (ecuación normal, dataset CSV, métricas y snapshot) y respaldo **MET/Keytel**, rangos y persistencia por usuario.
- Integración Flask: auth con CSRF, protección de sesión, dashboard, historial, perfil ampliado y catálogo MET versionado.
- Verificación de correo, recuperación de contraseña, exportación CSV, CSRF en APIs JSON, rate limiting y APIs de usuarios protegidas.
- **Paginación** del historial, **migraciones versionadas** e idempotentes, **backend de rate limiting** y **fallback SMTP → consola**.
- **Desglose explicable** del cálculo (MET/Keytel) al crear, listar y consultar cada registro.
- **Borrado seguro con papelera**: borrar mueve a papelera; permite **restaurar**, **borrar definitivamente** y **vaciar**, siempre con sesión + CSRF y solo sobre registros propios (migración v6).
- **Google Sign-In opcional**: botón en `/login`, flujo OAuth con `state`, verificación del ID token, vinculación por correo verificado, creación de cuentas GOOGLE y migración v7. Sin credenciales queda desactivado con `[POR DEFINIR]`.
- **Regresión lineal y análisis técnico (TC-43 a TC-51)**: CSV con 5 columnas, ecuación normal con `X` de unos, recuperación de coeficientes conocidos, MAE/RMSE/R², serialización de matrices y 3 gráficas, migración v8, `altura_cm`/`modelo_snapshot` en cada predicción, desglose histórico exacto, endpoint `/api/calorias/analisis`, flujo completo con altura del perfil y respaldo MET/Keytel.

---

## 👥 Metodología Mob Programming (4 Roles del Equipo)

En cada equipo de 4 estudiantes se rotan los roles cada 15 a 20 minutos:
1. **Piloto:** Opera el teclado y el IDE agéntico (Antigravity).
2. **Navegante / Prompter:** Formula las instrucciones y prompts de ingeniería a la IA.
3. **Arquitecto:** Custodia los contratos en `docs/` (`SPEC.md`, `ARCHITECTURE.md`, capas).
4. **Auditor QA:** Inspecciona cada `diff` (+ verde / - rojo) y ejecuta los tests en terminal.

---
**Universidad Adventista de Bolivia (UAB) — Carrera de Ingeniería de Sistemas**  
*Facilitador: Lic. Ulfredo Carlo Ramos (Willys - COMTECO R.L.)*
