# docs/API.md — Contratos de Interfaz y Firmas de Funciones (Etapa 5)
<!-- Willys_IA: Contratos de Interfaz y Firmas Tipadas - Taller UAB 2026 -->

## 1. Alcance de la Interfaz en el MVP (Flask Web + REST API)
El proyecto expone:
- **Rutas web (sesión):** autenticación y acceso a la plataforma interna (`src/main.py`, `src/templates/`).
- **APIs REST (JSON):** usuarios y predicción de calorías (`src/modulos/usuarios/`, `src/modulos/prediccion_calorias/`).
- Se mantiene el módulo base `gestion_mvp` del starter-kit (`/api/mvp`).

---

## 2. Rutas Web de Autenticación y Plataforma

### 2.1 Registro de cuenta
- **Ruta:** `GET|POST /registro`
- **Entrada (POST form):** `csrf_token`, `nombre` (str), `email` (str), `password` (str, >=8 con letras y números)
- **Servicio:** `Willys_IA_UsuarioService.registrar_usuario(nombre, email, password, rol="ESTUDIANTE", peso_preferido_kg=None, edad=None, sexo=None, fc_reposo=None)`
- **Seguridad:** valida token CSRF, aplica rate limiting por IP, crea usuario con hash, genera token de verificación (SMTP si está configurado; si no, consola) e inicia sesión
- **Éxito:** redirige a `/dashboard` | **Error:** `400` (CSRF/datos/correo duplicado) o `429` (rate limit)

### 2.2 Inicio y cierre de sesión
- **Rutas:** `GET|POST /login`, `GET /logout`
- **Entrada login (POST form):** `csrf_token`, `email`, `password`
- **Servicio:** `Willys_IA_UsuarioService.autenticar(email, password)`
- **Seguridad:** valida token CSRF y credenciales (usuario activo), con rate limiting por IP + correo
- **Éxito:** sesión iniciada → `/dashboard` | **Error:** `400` (CSRF), `401` (credenciales) o `429` (rate limit)

### 2.3 Inicio de sesión con Google (opcional)
- **Rutas:** `GET /google/login`, `GET /google/callback`
- **Activación:** requiere `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` y `GOOGLE_REDIRECT_URI` (por defecto se deriva del host: `.../google/callback`). Sin credenciales, `/login` muestra el botón desactivado y ambas rutas devuelven un mensaje `[POR DEFINIR]`. `GOOGLE_HD` opcional restringe el dominio; vacío acepta cualquier cuenta.
- **Seguridad:** genera un `state` aleatorio en sesión (10 min), valida el `state` anti-CSRF del callback, canjea el `code` por `id_token` y verifica firma/audiencia/emisor/expiración con `google-auth`. Rate limiting por IP (10/5 min).
- **Servicio:** `Willys_IA_UsuarioService.autenticar_google(claims)` busca por `google_sub`, vincula por correo verificado conservando contraseña/historial, o crea un usuario `GOOGLE` con contraseña aleatoria desconocida.
- **Éxito:** redirige a `/dashboard` con sesión iniciada | **Error:** `400` (state inválido/cancelado), `401` (token/correo no verificado), `429` (rate limit) o `500` (falta `google-auth`).

### 2.4 Dashboard protegido (plataforma interna)
- **Ruta:** `GET /dashboard`
- **Protección:** requiere sesión (`usuario_id`); si no existe, redirige a `/login`
- **Salida:** HTML `dashboard.html` con datos del usuario, estado de verificación, perfil (incluye altura), catálogo MET versionado, historial paginado y la sección **Análisis técnico · Regresión lineal múltiple** (dataset, matrices, ecuación, métricas y 3 gráficas con Chart.js local).

### 2.5 Verificación de correo y recuperación de contraseña
- **Verificación:** `GET /verificar/<token>` consume el token (24 h) y muestra el resultado; no requiere sesión.
- **Solicitud de recuperación:** `GET|POST /recuperar` (form con `csrf_token` + `email`); genera token de 60 min y lo envía por SMTP si está configurado o lo imprime en consola. Responde siempre un mensaje genérico (no revela si el correo existe).
- **Restablecimiento:** `GET|POST /reset/<token>` (form con `csrf_token`, `password`, `password_confirm`); valida token, coincidencia y política de contraseña.
- **Seguridad:** tokens aleatorios de un solo uso; rate limiting por IP en `/recuperar`.
- **SMTP opcional:** `src/notificaciones.py` envía por SMTP cuando `SMTP_HOST`/`SMTP_USER`/`SMTP_PASS` son credenciales reales; si faltan o fallan, cae a consola sin interrumpir el flujo. `[POR DEFINIR: proveedor de correo institucional y plantillas oficiales]`

---

## 3. API REST — Usuarios (`/api/usuarios`)

### 3.1 Registrar usuario
- **Endpoint:** `POST /api/usuarios` (público, limitado por IP)
- **Payload JSON:** `{"nombre":"...","email":"...","password":"...","rol":"ESTUDIANTE","peso_preferido_kg":70,"edad":21,"sexo":"M","fc_reposo":60}`
- **Firma Service:** `registrar_usuario(self, nombre, email, password, rol="ESTUDIANTE", peso_preferido_kg=None, edad=None, sexo=None, fc_reposo=None) -> Willys_IA_UsuarioModel`
- **Validaciones:** nombre >= 3, email válido y único, password >= 8 con letras y números, rol válido; perfil opcional en rango (peso <= 500, edad 10–120, sexo `M`/`F`/`OTRO`, FC 30–220)
- **Éxito:** `201 Created` con usuario serializado (sin `password_hash` ni tokens)
- **Error:** `400 Bad Request` `{"error":"..."}` | `429 Too Many Requests` por rate limiting

### 3.2 Listar usuarios
- **Endpoint:** `GET /api/usuarios`
- **Autenticación:** requerida (sesión). Sin sesión: `401`.
- **Éxito:** `200 OK` con lista JSON de usuarios (sin `password_hash` ni tokens)

### 3.3 Dar de baja usuario
- **Endpoint:** `POST /api/usuarios/<id_usuario>/baja`
- **Autenticación:** requerida (sesión) + header `X-CSRF-Token`. Sin sesión: `401` | sin CSRF: `403`.
- **Autorización:** un usuario solo puede darse de baja a sí mismo; un `ADMIN` puede dar de baja a cualquier usuario. Otro caso: `403`.
- **Éxito:** `200 OK` con confirmación (`estado: INACTIVO`)
- **Error:** `400 Bad Request` si el ID no existe | `403` CSRF/autorización

---

## 4. API REST — Predicción de Calorías (`/api/calorias`) [Protegida por sesión]

### 4.1 Listar historial de predicciones del usuario autenticado
- **Endpoint:** `GET /api/calorias`
- **Autenticación:** requerida (sesión). Si no hay sesión: `401 {"error":"No autenticado."}`
- **Query params opcionales:** `q` (texto/actividad), `actividad` (filtro parcial), `page` (>= 1, por defecto 1), `per_page` (1–100, por defecto 20; valores mayores se limitan a 100).
- **Firma Service:** `listar_paginado(self, usuario_id, q=None, actividad=None, page=1, per_page=20) -> dict`
- **Orden:** más reciente primero (`id DESC`). Si `page` supera el total, se ajusta a la última página disponible.
- **Alcance:** solo historial **activo**; los registros en papelera (`eliminado = 1`) quedan excluidos. Cada `item` incluye `eliminado` (false) y `fecha_eliminacion` (null).
- **Éxito:** `200 OK` con objeto paginado:
  ```json
  {
    "items": [{"id": 3, "tipo_actividad": "Correr", "calorias_estimadas": 350.0}],
    "total": 3,
    "page": 1,
    "per_page": 20,
    "total_pages": 1,
    "total_calorias": 583.35
  }
  ```
  `total_calorias` suma **todos** los registros filtrados, no solo la página. `total_pages` es `0` cuando no hay registros.
- **Desglose en cada `item`:** todos los registros incluyen `desglose` con:
  - `metodo` (`REGRESION`, `MET` o `KEYTEL`), `formula` (fórmula simbólica) y `sustitucion` (valores reales).
  - `valores`: `peso_kg`, `duracion_min`, `met`, `fc_promedio`, `edad`, `sexo` y `altura_cm` (los opcionales pueden ser `null`).
  - **Regresión:** `ecuacion`, `ecuacion_numerica`, `beta` (5 coeficientes), `vector_x`, `contribuciones`, `pasos` y `snapshot_usado`. Ejemplo: `"sustitucion": "-208.4387 + 2.5874·70 + 1.0479·170 - 1.3984·35 + 6.1936·45"`.
  - **Respaldo:** `horas` (MET) o `kcal_por_minuto` (Keytel). Ejemplo: `"sustitucion": "10.0 × 70.0 × (30.0 / 60)"` → `"resultado": 350.0`.
  - `resultado_sin_redondear`, `resultado` (2 decimales) y `nota` en todos los casos. El desglose de regresión usa el `modelo_snapshot` del registro, por lo que es estable aunque cambie el CSV.
- **Exportación CSV:** sigue devolviendo **todos** los registros filtrados (sin paginar).

### 4.2 Crear predicción de calorías
- **Endpoint:** `POST /api/calorias`
- **Autenticación:** requerida (sesión). Si no hay sesión: `401`
- **CSRF (JSON):** requiere header `X-CSRF-Token` con el token de `/api/csrf-token` o del dashboard; si falta o no coincide: `403`
- **Rate limiting:** 30 solicitudes por usuario cada 60 s; al excederse: `429`
- **Payload JSON:** `{"tipo_actividad":"Trotar","peso_kg":70,"duracion_min":45,"altura_cm":170,"met":7,"fc_promedio":145}`
- **Firma Service:** `predecir_y_guardar(self, usuario_id, tipo_actividad, peso_kg, duracion_min, met, fc_promedio=None, edad=None, sexo=None, altura_cm=None) -> Willys_IA_CaloriaModel`
- **Regla de cálculo (en orden de prioridad):**
  1. Con peso, **altura**, edad y duración: regresión lineal múltiple entrenada desde `data/dataset_calorias.csv` → `metodo_calculo='REGRESION'`. `Ŷ = β0 + β1·peso + β2·altura + β3·edad + β4·minutos`, con `β = (XᵀX)⁻¹ XᵀY`. Se guarda `altura_cm` y `modelo_snapshot` (JSON con los 5 coeficientes).
  2. Sin altura pero con `fc_promedio` (30–220), edad (10–120) y sexo (`M`/`F`): ecuación de Keytel → `metodo_calculo='KEYTEL'`.
     - Hombres: `kcal/min = (-55.0969 + 0.6309·FC + 0.1988·peso + 0.2017·edad) / 4.184`
     - Mujeres: `kcal/min = (-20.4022 + 0.4472·FC - 0.1263·peso + 0.0740·edad) / 4.184`
  3. Sin esos datos: `calorias_estimadas = MET × peso_kg × (duracion_min / 60)` → `metodo_calculo='MET'`.
  - La altura, la edad y el sexo se toman del perfil si el payload no los trae; el cliente solo envía `fc_promedio` y, opcionalmente, `altura_cm`.
- **Validaciones definidas:** actividad >= 3 chars; `0 < peso_kg <= 500`; `0 < duracion_min <= 1440`; MET válido (0.5–20, o resuelto desde catálogo); altura 100–250 cm; FC 30–220; edad 10–120.
- **Éxito:** `201 Created` con predicción guardada (incluye `metodo_calculo`, `altura_cm`, `modelo_snapshot`, `fc_promedio`, `edad`, `sexo` y `desglose`).
- **Error:** `400` datos inválidos | `403` CSRF | `429` rate limit.

### 4.3 Ver el desglose de un registro
- **Endpoint:** `GET /api/calorias/<id_registro>`
- **Autenticación:** requerida (sesión). Sin sesión: `401`.
- **Autorización:** solo devuelve registros del usuario autenticado; si no existe o es de otro usuario: `404`.
- **Incluye papelera:** un registro propio en papelera también es consultable y devuelve `eliminado: true` y su `fecha_eliminacion`.
- **Éxito:** `200 OK` con la predicción y su `desglose` (mismo contrato que el listado).
- **Uso en UI:** el botón «Ver cálculo» del historial y de la papelera consume este endpoint.

### 4.4 Borrar un registro (mover a papelera)
- **Endpoint:** `DELETE /api/calorias/<id_registro>`
- **Autenticación:** requerida (sesión). Sin sesión: `401`.
- **CSRF (JSON):** requiere header `X-CSRF-Token`; si falta o no coincide: `403`.
- **Rate limiting:** 30 movimientos por usuario cada 60 s; al excederse: `429`.
- **Autorización:** filtra por `id` **y** `usuario_id`. Si no existe, ya está en papelera o pertenece a otro usuario: `404` (no se revela su existencia).
- **Éxito:** `200 OK` con `{"eliminado": true, "en_papelera": true, "id": N, "mensaje": "El registro se movió a la papelera; puedes restaurarlo."}`.
- **Nota:** es una **eliminación suave**: el registro sale del historial y KPIs, pero se conserva en la papelera. La UI pide confirmación.

### 4.5 Listar la papelera
- **Endpoint:** `GET /api/calorias/papelera`
- **Autenticación:** requerida (sesión). Sin sesión: `401`.
- **Query params:** `q`, `actividad`, `page`, `per_page` (mismo contrato paginado que 4.1).
- **Éxito:** `200 OK` con `items`, `total`, `page`, `per_page`, `total_pages` y `total_calorias`; los `items` tienen `eliminado: true` y `fecha_eliminacion`, además del `desglose`.

### 4.6 Restaurar un registro
- **Endpoint:** `POST /api/calorias/<id_registro>/restaurar`
- **Autenticación:** requerida (sesión) + header `X-CSRF-Token`. Sin sesión `401` | sin CSRF `403`.
- **Rate limiting:** 30 restauraciones por usuario cada 60 s; al excederse: `429`.
- **Éxito:** `200 OK` con `{"restaurado": true, "id": N, "registro": {...}, "mensaje": "..."}`; el registro vuelve al historial activo y desaparece de la papelera.
- **Error:** `404` si el registro no está en la papelera del usuario | `403` CSRF.

### 4.7 Borrar definitivamente un registro de la papelera
- **Endpoint:** `DELETE /api/calorias/<id_registro>/definitivo`
- **Autenticación:** requerida (sesión) + header `X-CSRF-Token`. Sin sesión `401` | sin CSRF `403`.
- **Rate limiting:** 10 operaciones de purga por usuario cada 60 s; al excederse: `429`.
- **Autorización:** solo si el registro está en la papelera del usuario; en caso contrario: `404`.
- **Éxito:** `200 OK` con `{"eliminado_definitivamente": true, "id": N, "mensaje": "..."}`. Elimina la fila de SQLite; **no es recuperable**.

### 4.8 Vaciar la papelera
- **Endpoint:** `DELETE /api/calorias/papelera`
- **Autenticación:** requerida (sesión) + header `X-CSRF-Token`. Sin sesión `401` | sin CSRF `403`.
- **Rate limiting:** 10 operaciones de purga por usuario cada 60 s; al excederse: `429`.
- **Éxito:** `200 OK` con `{"eliminados": N, "mensaje": "..."}`. Afecta solo a los registros en papelera del usuario autenticado.

### 4.9 Exportar historial en CSV
- **Endpoint:** `GET /api/calorias/export.csv`
- **Autenticación:** requerida (sesión). Sin sesión: `401`.
- **Query params opcionales:** `q`, `actividad` (mismos filtros que el listado).
- **Respuesta:** `200 OK`, `Content-Type: text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="historial_calorias_<id>.csv"`.
- **Columnas:** Fecha, Actividad, Peso (kg), Altura (cm), Duración (min), MET, FC promedio (ppm), Edad, Sexo, Método, Calorías (kcal).
- **Aislamiento:** solo exporta registros **activos** del usuario autenticado (excluye la papelera).

### 4.10 Análisis técnico de la regresión
- **Endpoint:** `GET /api/calorias/analisis`
- **Autenticación:** requerida (sesión). Sin sesión: `401`. No requiere CSRF (solo lectura).
- **Rate limiting:** 30 consultas por usuario cada 60 s; al excederse: `429`.
- **Respuesta:** `200 OK` con:
  - `dataset`: `archivo` (`dataset_calorias.csv`), `ruta`, `filas` (80), `columnas` (`X_1`..`X_4`, `Y`), `columnas_descripcion`, `vista_previa` (8 filas), `estadisticas` (media, mediana, mínimo, máximo y desviación típica por columna) y `nota` (datos ficticios y anonimizados).
  - `matrices`: `X` (80×5, con columna de unos, 6 filas de vista previa), `XT` (5×80, 6 columnas), `Y` (80×1), `XTX` (5×5), `XTY` (5×1) y `beta` (5×1), con `dimensiones`, `columnas`/`simbolos`, `valores` o `vista_previa` y notas explicativas.
  - `formula_normal`: `β = (XᵀX)⁻¹ · XᵀY`; `nota_metodo` y `pasos` (5 pasos del cálculo).
  - `ecuacion`: `Ŷ = β0 + β1X1 + β2X2 + β3X3 + β4X4`; `ecuacion_numerica` con los coeficientes redondeados.
  - `interpretacion`: 5 entradas (`simbolo`, `variable`, `unidad`, `coeficiente`, `texto`) con el efecto de cada `β_i` manteniendo constantes las demás variables.
  - `metricas`: `MAE` (1.3155), `RMSE` (1.5224) y `R2` (0.9999) para el dataset actual.
  - `graficas`: `real_vs_predicho` y `residuos` (80 puntos `{x, y}` cada una) e `impacto` (4 coeficientes por variable). El dashboard las dibuja con `/static/chart.umd.min.js` (sin CDN).
- **Error:** `400/500` si el CSV falta, tiene columnas incorrectas o `XᵀX` no es invertible.

## 5. API REST — Perfil, Catálogo MET y CSRF (definidos)

### 5.1 Perfil del usuario
- **`GET /api/perfil`** (sesión): retorna `{"usuario": {...}}` con `peso_preferido_kg`, `altura_preferida_cm`, `edad`, `sexo`, `fc_reposo` y `email_verificado`. Nunca expone `password_hash` ni tokens.
- **`POST|PUT /api/perfil`** (sesión): actualiza uno o más campos de perfil.
  - **CSRF (JSON):** requiere header `X-CSRF-Token`; si falta o no coincide: `403`.
  - **Rate limiting:** 30 solicitudes por usuario cada 60 s; al excederse: `429`.
  - **Payload:** `{"peso_preferido_kg": 72.5, "altura_preferida_cm": 170, "edad": 21, "sexo": "M", "fc_reposo": 60}` (cada campo opcional; `null` lo limpia).
  - **Validaciones:** peso `> 0 y <= 500`; altura `100–250 cm`; edad `10–120`; sexo `M`/`F`/`OTRO`; FC de reposo `30–220`.
  - **Éxito:** `200 OK` con el usuario actualizado | **Error:** `400` datos inválidos | `403` CSRF | `429` rate limit.

### 5.2 Catálogo MET
- **`GET /api/met-catalogo`** (público): retorna `{"catalogo": {...}, "actividades": [{"key": "...", "nombre": "...", "met": N, "descripcion": "..."}, ...]}`.
- **Metadatos:** `catalogo.version` (`1.0.0`), `catalogo.fuente`, `catalogo.revision`, `catalogo.estado_validacion`, `catalogo.total_actividades` y `catalogo.rango_met`.
- **Estado:** referencia educativa basada en el *Compendium of Physical Activities*; no se declara como tabla institucional oficial. `[POR DEFINIR: validación con profesional/tabla UAB]`

### 5.3 Token CSRF para APIs JSON
- **`GET /api/csrf-token`**: retorna `{"csrf_token": "..."}` asociado a la sesión. El dashboard también lo expone en `<meta name="csrf-token">`.
- Las APIs JSON con sesión (`POST /api/calorias`, `DELETE /api/calorias/<id>`, `POST /api/calorias/<id>/restaurar`, `DELETE /api/calorias/<id>/definitivo`, `DELETE /api/calorias/papelera`, `POST|PUT /api/perfil`) exigen el header `X-CSRF-Token`. Las rutas de solo lectura (`GET`) no lo requieren.

---

## 6. API REST — Módulo base MVP (`/api/mvp`)
Se conserva para referencia del starter-kit:
- `GET /api/mvp` (filtro `?estado=`)
- `POST /api/mvp` (`nombre`, `categoria`, `valor`)
- `POST|PUT /api/mvp/<id>/estado`
- `GET /api/mvp/metricas`

---

## 7. Notas y [POR DEFINIR]

### Definido en el MVP
- **CSRF:** formularios web (`/login`, `/registro`, `/recuperar`, `/reset`) con token de sesión; APIs JSON con sesión (`POST /api/calorias`, `DELETE /api/calorias/<id>`, `POST /api/calorias/<id>/restaurar`, `DELETE /api/calorias/<id>/definitivo`, `DELETE /api/calorias/papelera`, `POST|PUT /api/perfil`) exigen header `X-CSRF-Token`. El flujo de Google usa además un `state` aleatorio en sesión. Token obtenible en `GET /api/csrf-token` y en el `<meta>` del dashboard.
- **Rate limiting (backend pluggable):** login 10/5 min por IP+correo; Google 10/5 min por IP; registro 10/10 min por IP; recuperación 5/10 min por IP; perfil, predicciones, consultas de análisis, movimientos a papelera y restauraciones 30/min por usuario; borrado definitivo y vaciado 10/min. Al excederse se responde `429`. Backend `RATE_LIMIT_BACKEND=auto|memory|redis`; con Redis configurado usa sorted sets atómicos y, ante fallos, cae a memoria.
- **Recuperación y verificación:** tokens aleatorios de un solo uso. Verificación de correo 24 h (`/verificar/<token>`), recuperación 60 min (`/recuperar` → `/reset/<token>`). Envío por SMTP si hay credenciales reales; en caso contrario, el enlace se imprime en consola. La solicitud de recuperación responde siempre un mensaje genérico para no revelar si el correo existe.
- **Exportación:** `GET /api/calorias/export.csv`, protegida por sesión, con BOM UTF-8 y filtros `q`/`actividad`; solo incluye registros del usuario autenticado.
- **Perfil ampliado:** `peso_preferido_kg`, `altura_preferida_cm`, `edad`, `sexo`, `fc_reposo` persistidos y validados (altura en migración v8).
- **Historial paginado:** `GET /api/calorias` acepta `page`/`per_page` (máx. 100) y devuelve `items`, `total`, `total_pages` y `total_calorias`; el dashboard consume ese contrato.
- **Cálculo explicable:** `Willys_IA_CaloriaService.serializar(item)` añade `desglose` a todas las respuestas de calorías. La fórmula se calcula en un único helper por método (`_calcular_regresion` o `_calcular`) para que el resultado y la explicación no se desincronicen; los registros de regresión guardan `modelo_snapshot` con los `β` exactos usados.
- **Regresión lineal y análisis técnico:** el modelo se entrena desde `data/dataset_calorias.csv` con `β = (XᵀX)⁻¹ XᵀY` (NumPy). `GET /api/calorias/analisis` publica matrices, dimensiones, interpretación, MAE/RMSE/R² y los datos de 3 gráficas; Chart.js se sirve desde `/static/chart.umd.min.js` para funcionar sin Internet.
- **Borrado con papelera:** `DELETE /api/calorias/<id>` solo marca `eliminado = 1` del usuario en sesión (CSRF + rate limiting + confirmación). La papelera permite `GET /api/calorias/papelera`, `POST /api/calorias/<id>/restaurar`, `DELETE /api/calorias/<id>/definitivo` y `DELETE /api/calorias/papelera`; migración v6. `[POR DEFINIR: retención automática de la papelera y auditoría de eliminaciones]`
- **Migraciones versionadas:** `database.MIGRACIONES` se aplica en orden y queda registrada en `schema_migrations`; es idempotente y compatible con bases anteriores.
- **APIs de usuarios:** `POST /api/usuarios` es público (registro) con rate limit; `GET /api/usuarios` y `POST /api/usuarios/<id>/baja` requieren sesión, y la baja exige CSRF y autorización (propia cuenta o `ADMIN`).

### Pendiente
- `[POR DEFINIR: proveedor de correo SMTP institucional, credenciales y plantillas de mensaje reales]`
- `[POR DEFINIR: despliegue con Redis y proxy inverso en producción; el backend ya es pluggable]`
- `[POR DEFINIR: autenticación por token (JWT/OAuth) para clientes externos; el MVP usa sesión de Flask]`
- `[POR DEFINIR: migración a PostgreSQL/ORM para despliegue multiusuario]`

