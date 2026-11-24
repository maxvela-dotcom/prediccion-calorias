# docs/SPEC.md — Contrato Técnico de Especificación Formal (Etapa 2)
<!-- Willys_IA: Contrato Inviolable de Requerimientos - Taller UAB 2026 -->
<!-- REGLA #2: Lo que no esté definido con certeza se marca [POR DEFINIR], ¡jamás se inventa! -->

## 1. Descripción del Sistema
> **Resumen Ejecutivo (2 líneas):**
> *Sistema web local **"Calorías en Rutina"** para que una persona estime las calorías quemadas en sus rutinas de ejercicio.*
> *Incluye registro e inicio de sesión de usuarios; la plataforma interna (dashboard e historial) solo es visible tras autenticarse.*

---

## 2. Problema y Dolor que Resuelve (Alineado con docs/IDEA.md)
- **Situación actual:** Las personas registran sus entrenamientos y estiman calorías de forma manual o dispersa (notas, hojas de cálculo), sin historial centralizado ni acceso personal protegido.
- **Objetivo del MVP:** Permitir que un usuario cree su cuenta, inicie sesión y en menos de 1 minuto registre una rutina para obtener una estimación de calorías y verla en su historial personal.

---

## 3. Usuarios y Actores del MVP
| Actor | Rol en el Sistema | Permisos en el MVP |
| :--- | :--- | :--- |
| **Usuario registrado** | Persona que entrena y desea estimar calorías | Crear cuenta, iniciar/cerrar sesión, registrar rutinas, ver su historial y filtrar predicciones |
| **Visitante (no autenticado)** | Persona sin sesión activa | Acceder solo a registro e inicio de sesión (sin acceso al dashboard/API protegida) |

---

## 4. Alcance Estricto del MVP (In-Scope vs Out-of-Scope)

### 4.1 LO QUE SÍ HACE EL MVP
- [x] **RF-01 (Cuenta y acceso):** Registrar usuario con nombre, correo único y contraseña (hash); iniciar y cerrar sesión. El login ofrece además **Continuar con Google** como opción opcional: flujo OAuth con `state`, verificación del ID token en servidor, vinculación por correo verificado y creación de cuentas `GOOGLE`. `[POR DEFINIR: credenciales de Google Cloud para activarlo]`
- [x] **RF-02 (Predicción de calorías):** Registrar una rutina (actividad, peso, altura, duración, MET y FC promedio opcional) y calcular calorías con un modelo explicable: **regresión lineal múltiple** entrenada desde CSV como método principal, con respaldo MET/Keytel. Mostrar el **desglose** (fórmula, coeficientes, valores sustituidos, aportes y resultado) al crear y al consultar cada registro.
- [x] **RF-03 (Historial personal):** Listar predicciones del usuario autenticado de forma **paginada**, con filtros básicos (actividad/texto), totales y **exportación CSV** (incluye la altura usada).
- [x] **RF-04 (Perfil ampliado):** Guardar peso, altura, edad, sexo y FC de reposo; la altura/edad habilitan la regresión y la edad/sexo/FC promedio habilitan Keytel como respaldo.
- [x] **RF-07 (Análisis técnico visible):** Cargar el dataset CSV, entrenar la regresión con `β = (XᵀX)⁻¹XᵀY` y mostrar en `/dashboard` y `/api/calorias/analisis` el dataset y sus estadísticos, `X` (con unos), `Xᵀ`, `Y`, `XᵀX`, `XᵀY`, `β` con dimensiones, la ecuación, la interpretación de cada coeficiente, MAE/RMSE/R² y al menos 2 gráficas (3 implementadas).
- [x] **RF-05 (Verificación y recuperación):** Generar enlaces de verificación de correo y de restablecimiento de contraseña con tokens de un solo uso. El envío por **SMTP es opcional**; si no hay credenciales, el enlace se imprime en consola.
- [x] **RF-06 (Papelera y recuperación):** El usuario autenticado puede mover una predicción a la papelera (`DELETE /api/calorias/<id>`), consultarla (`GET /api/calorias/papelera`), restaurarla (`POST /api/calorias/<id>/restaurar`), borrarla definitivamente (`DELETE /api/calorias/<id>/definitivo`) o vaciar la papelera (`DELETE /api/calorias/papelera`). Todas las operaciones exigen sesión, CSRF y verificación de propiedad. `[POR DEFINIR: retención automática y auditoría de eliminaciones]`

### 4.2 LO QUE QUEDA EXPLÍCITAMENTE FUERA (Out-of-Scope del MVP actual)
- ❌ **Sin despliegue en nube:** ejecución local con persistencia en **SQLite** (`data/app.db`).
- ❌ **Sin proveedor de identidad obligatorio:** la autenticación propia con correo/contraseña sigue funcionando siempre; **Google Sign-In es opcional** y solo se activa con credenciales externas. `[POR DEFINIR: decisión de hacer Google obligatorio en el futuro]`
- ❌ **Sin librerías de ML ni nube:** la regresión se resuelve con álgebra lineal explícita en NumPy sobre un CSV local; no hay `sklearn`, entrenamiento remoto ni datos personales reales.
- ❌ **Sin envío de correo obligatorio:** SMTP es opcional; verificación y recuperación funcionan en modo local imprimiendo el enlace en consola si no hay credenciales. `[POR DEFINIR: proveedor SMTP/institucional y plantillas]`
- ❌ **Sin app móvil nativa.**

---

## 5. Requisitos No Funcionales (RNF) Medibles
1. **RNF-01 (Tiempo de Respuesta):** Consultas y cálculos con datos del laboratorio responden en menos de 1 segundo.
2. **RNF-02 (Robustez y Manejo Defensivo):** Entradas inválidas (campos vacíos, valores <= 0, formatos erróneos) devuelven errores controlados (`ValueError`/HTTP 400) sin `Traceback` crudo al usuario.
3. **RNF-03 (Privacidad y Seguridad básica):** Contraseñas almacenadas como hash (no texto plano), política mínima (>= 8 caracteres con letras y números), protección CSRF en formularios web y APIs JSON con sesión (`X-CSRF-Token`), rate limiting pluggable en rutas sensibles (memoria por defecto, Redis opcional con fallback), cookies de sesión `HttpOnly`/`SameSite=Lax`; acceso a dashboard e historial solo con sesión válida.
4. **RNF-04 (Trazabilidad del método):** Cada predicción registra `metodo_calculo` (`REGRESION`, `MET` o `KEYTEL`), los parámetros usados (altura, FC, edad, sexo) y, para regresión, un `modelo_snapshot` con los `β` exactos. La API y el dashboard exponen un `desglose` reconstruible con la fórmula, la ecuación numérica, la sustitución de valores, los aportes por término y el resultado redondeado a 2 decimales.
5. **RNF-05 (Transparencia del modelo):** El análisis técnico muestra las dimensiones de `X` (n×5), `Xᵀ` (5×n), `XᵀX`, `XᵀY` y `β`, interpreta cada coeficiente en contexto y reporta MAE, RMSE y R²; las gráficas funcionan sin conexión a Internet.

---

## 6. Reglas de Negocio Inviolables (RN)
- **RN-01 (Cuenta válida):** `nombre` >= 3 caracteres, `email` con formato válido y **único**, `password` >= 8 caracteres con al menos una letra y un número.
- **RN-02 (Acceso protegido):** El dashboard y las APIs internas (`/api/calorias`, `/api/perfil`, `GET /api/usuarios`, `POST /api/usuarios/<id>/baja`) requieren usuario autenticado en sesión; los formularios web validan token CSRF y las APIs JSON con sesión exigen el header `X-CSRF-Token`. La baja de usuarios solo procede sobre la propia cuenta o por un `ADMIN`.
- **RN-03 (Datos de rutina válidos):** `tipo_actividad` no vacío (>= 3), `peso_kg > 0` y `<= 500`, `altura_cm` (si se envía) `100` a `250`, `duracion_min > 0` y `<= 1440`, `met` en rango válido (`0.5` a `20`).
- **RN-04 (Regresión lineal múltiple):** con peso (X1), altura (X2), edad (X3) y duración (X4) se entrena `β = (XᵀX)⁻¹ XᵀY` desde `data/dataset_calorias.csv` y se predice `Ŷ = β0 + β1X1 + β2X2 + β3X3 + β4X4` (redondeado a 2 decimales). Si `XᵀX` no es invertible, se rechaza con error controlado. Se guarda el vector β usado en `modelo_snapshot`.
- **RN-05 (Respaldo MET y Keytel):** si falta altura o edad pero hay `fc_promedio` (30–220 ppm), `edad` (10–120) y `sexo` (`M`/`F`), se aplica la **ecuación de Keytel** (`metodo_calculo='KEYTEL'`); si faltan esos datos, se usa `calorias_estimadas = MET × peso_kg × (duracion_min / 60)` (`metodo_calculo='MET'`). El catálogo MET versionado (`src/modulos/prediccion_calorias/met_catalogo.py`, basado en *Compendium of Physical Activities*, simplificado) expone versión/fuente/revisión y resuelve MET desde la actividad.
- **RN-06 (Historial y perfil personal):** Un usuario solo puede consultar/registrar sus predicciones; el historial se pagina (`page`/`per_page`, máx. 100) y puede guardar `peso_preferido_kg`, `altura_preferida_cm`, `edad`, `sexo` y `fc_reposo` en su perfil, usados por la plataforma como predictores cuando la rutina no los especifica.
- **RN-07 (Tokens de un solo uso):** Verificación de correo (24 h) y recuperación de contraseña (60 min) usan tokens aleatorios de un solo uso; el restablecimiento exige la misma política de contraseña.
- **RN-08 (Exportación):** El usuario autenticado puede descargar su historial completo en CSV; la exportación respeta los filtros `q` y `actividad` y nunca incluye datos de otros usuarios.
- **RN-09 (Rate limiting):** Login, registro, recuperación, perfil y predicciones tienen límites de intentos en ventanas de tiempo; al excederse responden `429`. El backend es pluggable (`memory`/`redis`) con fallback seguro a memoria.
- **RN-10 (Migraciones):** Todo cambio de esquema SQLite se registra como una migración versionada en `schema_migrations`; deben ser idempotentes y compatibles con bases existentes. La versión 8 agrega `altura_cm` y `modelo_snapshot` a las predicciones y `altura_preferida_cm` al perfil.
- **RN-11 (Dataset anonimizado):** `data/dataset_calorias.csv` contiene 80 filas ficticias con columnas `X_1,X_2,X_3,X_4,Y`; no se almacenan datos personales reales y su modificación requiere reentrenar el modelo y revisar las métricas publicadas.

---

## 7. Modelo de Datos Conceptual

### 7.1 Entidad: USUARIO
| Campo | Tipo | Restricción / Formato | Obligatorio | Descripción |
| :--- | :---: | :--- | :---: | :--- |
| `id` | `int` | PK, autoincremental > 0 | Sí | Identificador único |
| `nombre_completo` | `str` | NOT NULL, len >= 3 | Sí | Nombre del usuario |
| `email` | `str` | NOT NULL, UNIQUE, formato correo | Sí | Credencial de acceso |
| `password_hash` | `str` | NOT NULL | Sí | Hash seguro de contraseña |
| `rol` | `str` | Valores permitidos | Sí | Rol (ej. ESTUDIANTE) |
| `estado` | `str` | `ACTIVO` \| `INACTIVO` | Sí | Estado de cuenta |
| `peso_preferido_kg` | `float?` | NULL o ( > 0 y <= 500 ) | No | Preferencia de perfil; X1 de la regresión |
| `altura_preferida_cm` | `float?` | NULL o (100 a 250) | No | Altura del perfil (v8); X2 de la regresión |
| `edad` | `int?` | NULL o (10 a 120) | No | Edad para la regresión (X3) y Keytel |
| `sexo` | `str?` | NULL, `M` \| `F` \| `OTRO` | No | Sexo para la ecuación de Keytel (respaldo) |
| `fc_reposo` | `float?` | NULL o (30 a 220 ppm) | No | FC de reposo del perfil |
| `email_verificado` | `int` | 0 \| 1 (default 0) | Sí | Estado de verificación del correo |
| `token_verificacion` | `str?` | Token de un solo uso | No | Token vigente de verificación (24 h) |
| `token_expira` | `str?` | Timestamp | No | Expiración del token de verificación |
| `reset_token` | `str?` | Token de un solo uso | No | Token vigente de recuperación (60 min) |
| `reset_expira` | `str?` | Timestamp | No | Expiración del token de recuperación |
| `fecha_registro` | `str` | Timestamp | Sí | Fecha de creación |

### 7.2 Entidad: PREDICCION_CALORIA
| Campo | Tipo | Restricción / Formato | Obligatorio | Descripción |
| :--- | :---: | :--- | :---: | :--- |
| `id` | `int` | PK, autoincremental > 0 | Sí | Identificador único |
| `usuario_id` | `int` | FK lógica a USUARIO.id | Sí | Propietario de la predicción |
| `tipo_actividad` | `str` | NOT NULL, len >= 3 | Sí | Actividad realizada |
| `peso_kg` | `float` | > 0 | Sí | Peso usado en el cálculo |
| `duracion_min` | `float` | > 0 | Sí | Duración de la rutina |
| `met` | `float` | > 0 | Sí | Equivalente metabólico (respaldo) |
| `fc_promedio` | `float?` | NULL o (30–220 ppm) | No | FC promedio usada por Keytel |
| `edad` | `int?` | NULL o (10–120) | No | Edad usada como X3 en la regresión |
| `sexo` | `str?` | NULL, `M` \| `F` \| `OTRO` | No | Sexo usado por Keytel |
| `altura_cm` | `float?` | NULL o (100–250), obligatoria si `REGRESION` (v8) | No | Altura usada como X2 en la regresión |
| `modelo_snapshot` | `str?` | NULL o JSON con `beta` de 5 coeficientes (v8) | No | Coeficientes usados al predecir, para desgloses históricos |
| `metodo_calculo` | `str` | `REGRESION` \| `MET` \| `KEYTEL` | Sí | Ecuación aplicada |
| `calorias_estimadas` | `float` | >= 0 | Sí | Resultado estimado (kcal) |
| `fecha_registro` | `str` | Timestamp | Sí | Fecha de la predicción |

---

## 8. Criterios de Aceptación Verificables (Given · When · Then)

### Criterio 1: Registro y acceso a plataforma
- **Dado** un visitante con nombre, correo único y contraseña válida (>= 8, con letras y números),
- **Cuando** completa el registro,
- **Entonces** el sistema crea la cuenta (hash), inicia sesión y redirige al dashboard protegido.

### Criterio 2: Bloqueo sin autenticación
- **Dado** un visitante sin sesión activa,
- **Cuando** intenta acceder a `/dashboard`, `/api/calorias` o `/api/calorias/export.csv`,
- **Entonces** el sistema redirige a `/login` o responde HTTP 401 (no expone datos internos).

### Criterio 3: Predicción válida de calorías (respaldo MET)
- **Dado** un usuario autenticado con `peso_kg=70`, `duracion_min=60`, `met=8`, sin altura/edad en el perfil y sin FC promedio,
- **Cuando** registra la rutina,
- **Entonces** el sistema guarda la predicción con `calorias_estimadas=560.00`, `metodo_calculo='MET'` y la muestra en su historial.

### Criterio 4: Rechazo de datos inválidos
- **Dado** un usuario autenticado que ingresa `peso_kg<=0`, `duracion_min<=0`, `met` fuera de rango o actividad vacía,
- **Cuando** envía el formulario,
- **Entonces** el sistema rechaza la operación con error controlado y no altera el historial.

### Criterio 5: Predicción con ecuación de Keytel (sin altura)
- **Dado** un usuario con `edad=30`, `sexo=M`, sin altura registrada y una rutina con `fc_promedio=150`, `peso_kg=70`, `duracion_min=30`,
- **Cuando** registra la rutina,
- **Entonces** el sistema aplica Keytel, guarda `metodo_calculo='KEYTEL'` y el resultado calculado.

### Criterio 6: Exportación CSV
- **Dado** un usuario autenticado con predicciones,
- **Cuando** solicita `/api/calorias/export.csv` (con o sin filtros),
- **Entonces** recibe un archivo CSV con solo sus registros y las columnas definidas.

### Criterio 7: Verificación y recuperación
- **Dado** un usuario registrado,
- **Cuando** se genera un enlace de verificación o recuperación,
- **Entonces** el enlace se envía por SMTP si está configurado o se imprime en la consola local; es de un solo uso y expira (24 h / 60 min).

### Criterio 8: CSRF y rate limiting
- **Dado** un usuario autenticado,
- **Cuando** envía un POST JSON sin `X-CSRF-Token` o excede el límite de intentos,
- **Entonces** el sistema responde `403` (CSRF) o `429` (rate limit) sin ejecutar la operación.

### Criterio 9: Paginación del historial
- **Dado** un usuario con más predicciones que `per_page`,
- **Cuando** solicita `/api/calorias?page=2&per_page=5`,
- **Entonces** recibe solo la página solicitada (más reciente primero), junto con `total`, `total_pages` y `total_calorias` de todos los registros filtrados.

### Criterio 10: Migraciones y catálogo versionado
- **Dado** una base existente o nueva,
- **Cuando** inicia la aplicación,
- **Entonces** las migraciones pendientes se aplican una sola vez y quedan en `schema_migrations` (incluida la v8 de regresión); `/api/met-catalogo` expone `version`, `fuente` y `revision` del catálogo.

### Criterio 11: Regresión lineal y análisis técnico
- **Dado** un usuario autenticado con peso, altura, edad y duración en una rutina,
- **Cuando** registra la rutina y abre el análisis técnico del dashboard,
- **Entonces** se guarda `metodo_calculo='REGRESION'` con `altura_cm` y `modelo_snapshot`; la respuesta y el historial muestran el desglose con β, vector `x`, aportes y resultado; `/api/calorias/analisis` devuelve las matrices con sus dimensiones, la interpretación de cada coeficiente, MAE/RMSE/R² y los datos de 3 gráficas.

---

## 9. Supuestos, Riesgos y Aspectos [POR DEFINIR]
- **Definido:** catálogo MET versionado y reglas/rangos de cálculo (`met_catalogo.py`, MET 0.5–20, versión 1.0.0). `[POR DEFINIR: adopción de tabla institucional oficial y validación profesional]`
- **Definido:** persistencia local en **SQLite** con inicialización automática (`src/database.py`, `data/app.db`) y **migraciones versionadas** en `schema_migrations`. `[POR DEFINIR: paso a PostgreSQL/ORM en despliegue]`
- **Definido:** perfil ampliado (`peso_preferido_kg`, `altura_preferida_cm`, `edad`, `sexo`, `fc_reposo`) persistido y gestionado por `/api/perfil`.
- **Definido:** **regresión lineal múltiple** entrenada desde `data/dataset_calorias.csv` (80 filas ficticias) con `β = (XᵀX)⁻¹XᵀY`, ecuación `Ŷ = β0 + β1X1 + β2X2 + β3X3 + β4X4`, desglose con snapshot de coeficientes y análisis técnico con 3 gráficas locales. `[POR DEFINIR: dataset real y validación profesional]`
- **Definido:** respaldo con **ecuación de Keytel** cuando hay FC promedio, edad y sexo pero no altura; fallback final a MET.
- **Definido:** seguridad endurecida (hash, política de contraseña >=8 con letras/números, CSRF en formularios y APIs JSON, cookies seguras, rate limiting pluggable con fallback).
- **Definido:** verificación de correo y recuperación de contraseña con tokens de un solo uso y **SMTP opcional** (fallback a consola).
- **Definido:** exportación CSV del historial con filtros, protegida por sesión.
- **Definido:** paginación del historial vía `page`/`per_page` (máx. 100).
- `[POR DEFINIR: proveedor SMTP institucional, credenciales reales y plantillas de mensaje]`
- `[POR DEFINIR: despliegue con Redis y proxy inverso; el backend de rate limiting ya es pluggable]`
- `[POR DEFINIR: sustituir el dataset ficticio por mediciones reales anonimizadas y validar la regresión con profesionales]`
- `[POR DEFINIR: credenciales reales de Google Cloud para activar el botón de acceso con Google]`
- **Riesgo:** Las estimaciones (regresión, MET y Keytel) son aproximadas y no sustituyen evaluación profesional; el dataset de entrenamiento es ficticio. **Mitigación:** mostrarlas como estimación educativa, registrar el método y los coeficientes usados, permitir ajustar MET y publicar las métricas del modelo.

