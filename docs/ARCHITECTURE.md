# docs/ARCHITECTURE.md — Diseño de Arquitectura y Decisiones (Etapa 3)
<!-- Willys_IA: Documento de Arquitectura y Trazabilidad Técnica - Taller UAB 2026 -->
<!-- PRINCIPIO DE ETAPA 3:
     Arquitectura no es sobreingeniería; es responder 3 decisiones independientes:
     1. Despliegue: Monolito ejecutable (la opción recomendada para 4h).
     2. Organización interna: Monolito Modular en Capas (Controller -> Service -> Repository -> Model).
     3. Comunicación: Llamadas a métodos tipados (o REST si frontend y backend están separados).
-->

## 1. Visión General: Monolito Modular en Capas
El sistema se diseña bajo un patrón de **Monolito Modular por Capas**, el estándar moderno de la industria que prepara a los estudiantes para trabajar con frameworks empresariales como Spring Boot (Java) o FastAPI (Python).

Cada módulo del sistema agrupa sus responsabilidades en 4 capas limpias:

```
+-----------------------------------------------------------------------------------+
|                        1. CAPA DE PRESENTACIÓN / CONTROL                          |
|   (src/main.py · *_controller.py · security.py · templates/*.html · Willys_IA)      |
|   - Recibe la entrada del usuario o cliente (formulario web o endpoint JSON).      |
|   - Maneja defensivamente las excepciones y devuelve respuestas legibles.         |
|   - Aplica CSRF, sesión y rate limiting antes de delegar en el servicio.          |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        2. CAPA DE SERVICIO / NEGOCIO                              |
|      (usuario_service.py · caloria_service.py · mvp_service.py · Willys_IA)        |
|   - Aplica rigurosamente las Reglas Inviolables del SPEC.md (RN-01 a RN-09).      |
|   - Valida datos de entrada y orquesta los casos de uso del módulo.               |
|   - NO accede a la base de datos directamente; delega en el repositorio.          |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     3. CAPA DE PERSISTENCIA / REPOSITORIO                         |
|     (usuario_repository.py · caloria_repository.py · mvp_repository.py)            |
|   - Ejecuta las operaciones de almacenamiento (guardar, buscar, filtrar).         |
|   - Persistencia local en SQLite (`data/app.db`) mediante `database.py`.           |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                       4. CAPA DE DOMINIO / MODELO                                 |
|          (usuario_model.py · caloria_model.py · mvp_model.py · Willys_IA)           |
|   - Define las entidades con tipado estricto (@dataclass / typing).               |
|   - Contiene la validación intrínseca de integridad de la entidad.                |
+-----------------------------------------------------------------------------------+
```

---

## 2. Descripción de Componentes y Nomenclatura Explícita

Para evitar el problema de "pestañas gemelas" (*Tab Confusion*) en el editor cuando varias capas están abiertas, cada archivo lleva el prefijo de su módulo:

| Componente / Archivo | Capa | Responsabilidad Principal |
| :--- | :--- | :--- |
| `src/main.py` | Entrada Global | Factoría Flask, sesión, CSRF, rutas web (login/registro/dashboard/verificación/reset) y APIs de perfil/CSRF. |
| `src/database.py` | Infraestructura | Conexión SQLite, creación de tablas y migraciones versionadas (`schema_migrations`). |
| `src/security.py` | Seguridad transversal | Rate limiting pluggable (memoria/Redis con fallback), validación CSRF y generación de tokens de un solo uso. |
| `src/notificaciones.py` | Infraestructura | Envío SMTP opcional con fallback a consola para verificación/recuperación. |
| `src/modulos/usuarios/google_auth.py` | Integración opcional | Construye la URL de Google, genera/valida el `state`, canjea el código y verifica el ID token con `google-auth` (importación diferida). |
| `src/modulos/prediccion_calorias/regresion_lineal.py` | Modelo analítico | Carga `data/dataset_calorias.csv`, construye `X` con unos, calcula `Xᵀ`, `XᵀX`, `XᵀY` y `β = (XᵀX)⁻¹XᵀY` con NumPy; expone métricas, coeficientes, snapshot y serialización para la UI. |
| `src/static/chart.umd.min.js` | Vista (Frontend) | Chart.js servido localmente para las 3 gráficas del análisis técnico (sin dependencia de CDN). |
| `src/templates/*.html` | Vista (Frontend) | `login`, `register`, `recuperar`, `reset`, `mensaje` (públicas) y `dashboard` (protegido, con formulario, historial y análisis técnico). |
| `*_controller.py` | Controlador / REST | Blueprints Flask (`/api/mvp`, `/api/usuarios`, `/api/calorias`); recibe requests, publica `/api/calorias/analisis` y controla errores. |
| `usuario_service.py` / `caloria_service.py` | Lógica de Negocio | Reglas de usuarios, perfil, tokens, autenticación; regresión como método principal con respaldo MET/Keytel, desglose con snapshot y exportación CSV. |
| `*_repository.py` | Persistencia | Almacena y consulta entidades en SQLite, garantizando IDs autoincrementales y unicidad. |
| `*_model.py` | Entidad / Dominio | Representa el dato del negocio con tipado, validación de atributos y serialización JSON. |
| `tests/test_app.py` | Calidad (QA) | Suite de 53 pruebas (TC-01 a TC-51): Unit Tests de capas, regresión/CSV/métricas e Integration Tests con `client.test_client()`. |

---

## 3. Flujo del Caso de Uso Principal (Paso a Paso)
1. **El usuario** abre `http://127.0.0.1:5000` en el navegador; la raíz redirige a `/login`. Puede crear cuenta en `/registro`.
2. **`main.py`** valida el token CSRF del formulario, aplica rate limiting por IP y delega en `usuario_service.py` (`registrar_usuario`).
3. **`usuario_service.py`** valida nombre/correo/contraseña, genera el hash con `werkzeug.security` y llama a `usuario_repository.py`, que persiste en SQLite.
4. Tras autenticarse, **`/dashboard`** (protegido por sesión) muestra perfil, estado de verificación, catálogo MET versionado, historial paginado y la sección de análisis técnico.
5. **`dashboard.html`** envía `POST /api/calorias` con `fetch()` y header `X-CSRF-Token`, y consulta `GET /api/calorias/analisis` para pintar tablas y gráficas con Chart.js local.
6. **`caloria_controller.py`** verifica sesión, CSRF y rate limiting; toma altura/edad/sexo del perfil si el payload no los trae y delega en `caloria_service.py`.
7. **`caloria_service.py`** aplica **regresión lineal múltiple** cuando están los 4 predictores (peso, altura, edad, minutos); si no, degrada a **Keytel** o **MET**. Valida rangos, guarda `modelo_snapshot` con los `β` usados y delega en `caloria_repository.py`, registrando `metodo_calculo`.
8. El controlador responde `201` con la predicción y su desglose; la página actualiza la tabla paginada, KPIs y permite **exportar CSV** (`/api/calorias/export.csv`). El desglose histórico se reconstruye con el snapshot del registro, no con los coeficientes actuales del CSV.

---

## 4. Registro de Decisión de Arquitectura (ADR-001)

### ADR-001: Adopción del Patrón Monolito Modular en Capas
- **Estado:** `APROBADO`
- **Fecha:** 2026-11-10
- **Contexto:**
  Los estudiantes necesitan aprender la separación de responsabilidades que encontrarán en el mercado laboral (Spring Boot, NestJS, FastAPI), pero dentro de un entorno ejecutable en 4 horas sin la sobrecarga de instalar servidores remotos.
- **Decisión:**
  Se adopta un **Monolito Modular por Capas (`controller` -> `service` -> `repository` -> `model`)**.
- **Alternativas Descartadas:**
  - *Microservicios:* Descartados por latencia de red y complejidad operativa desproporcionada para 4 horas.
  - *Script plano sin capas:* Descartado porque impide escribir pruebas unitarias independientes para la lógica de negocio.
- **Consecuencias Positivas:**
  1. Si en el futuro se cambia la consola por una API Web o interfaz gráfica, solo se toca el `controller` o la vista; el `service` y el `repository` permanecen intactos.
  2. Cada capa se puede probar de forma unitaria con `pytest` / `unittest`.
  3. Facilita que la IA implemente funciones de forma guiada sin tocar archivos ajenos.

---

## 5. Registro de Decisión de Arquitectura (ADR-002)

### ADR-002: Modelo de estimación MET con extensión a la ecuación de Keytel
- **Estado:** `APROBADO`
- **Fecha:** 2026-11-16
- **Contexto:**
  El MVP necesita una estimación explicable y comprobable sin entrenar un modelo de machine learning. La fórmula MET solo usa actividad, peso y duración; se dispone de edad, sexo y FC promedio en el perfil/rutina.
- **Decisión:**
  Usar **MET** como línea base (`MET × peso × min/60`) y aplicar la **ecuación de Keytel et al. (2005)** cuando existan FC promedio, edad y sexo (`M`/`F`). Registrar `metodo_calculo` (`MET`/`KEYTEL`) y los parámetros usados.
- **Alternativas Descartadas:**
  - *Modelo ML entrenado:* sin dataset institucional ni tiempo de entrenamiento en el taller.
  - *Solo Keytel:* exige FC y datos completos; dejaría fuera a usuarios sin esos datos.
- **Consecuencias Positivas:**
  1. Resultado reproducible y auditable para la evaluación académica.
  2. Degradación controlada: sin FC/edad/sexo se sigue obteniendo una estimación por MET.
  3. Preparado para una futura calibración con más variables; la calibración con regresión se materializó en ADR-003, conservando MET/Keytel como respaldo. `[POR DEFINIR: precisión aceptable y validación con datos reales]`

---

## 6. Registro de Decisión de Arquitectura (ADR-003)

### ADR-003: Regresión lineal múltiple con ecuación normal y trazabilidad del modelo
- **Estado:** `APROBADO`
- **Fecha:** 2026-11-23
- **Contexto:**
  La rúbrica de la evaluación final exige un dataset CSV, un modelo entrenado con álgebra lineal explícita y análisis técnico visible. MET/Keytel son fórmulas poblacionales fijas: no aprenden de datos ni permiten mostrar matrices, coeficientes estimados ni métricas de ajuste.
- **Decisión:**
  - Entrenar un modelo con **80 filas ficticias y anonimizadas** en `data/dataset_calorias.csv`: X1 peso (kg), X2 altura (cm), X3 edad (años), X4 minutos, Y calorías.
  - Resolver `β = (XᵀX)⁻¹ XᵀY` con NumPy de forma explícita (sin `sklearn` ni optimizadores), construyendo `X` con una columna de unos para el intercepto. Predecir con `Ŷ = β0 + β1X1 + β2X2 + β3X3 + β4X4`.
  - Usar la regresión como **método principal** cuando estén los 4 predictores; conservar **Keytel** y **MET** para registros antiguos o perfiles incompletos.
  - Guardar en cada predicción `altura_cm` y un `modelo_snapshot` con los `β` usados, para que el desglose histórico sea exacto aunque el CSV cambie (migración v8).
  - Publicar `GET /api/calorias/analisis` y mostrar en `/dashboard` matrices, dimensiones, interpretación de coeficientes, MAE/RMSE/R² y 3 gráficas con Chart.js servido localmente.
- **Alternativas Descartadas:**
  - *scikit-learn / gradient descent:* ocultan la ecuación normal y añaden una dependencia pesada; el objetivo pedagógico es auditar el álgebra.
  - *Reemplazar MET/Keytel por regresión:* rompería el historial existente y dejaría sin estimación a usuarios sin altura.
  - *Chart.js por CDN:* fallaría en el laboratorio sin Internet; se vendorizó el bundle en `src/static/`.
- **Consecuencias Positivas:**
  1. El estudiante puede ver y verificar cada paso: `X`, `Xᵀ`, `XᵀX`, `XᵀY`, `β`, dimensiones y métricas.
  2. Resultados reproducibles (MAE 1.3155, RMSE 1.5224, R² 0.9999) y explicables coeficiente por coeficiente.
  3. Degradación controlada y compatibilidad hacia atrás gracias al snapshot de coeficientes.
- **Consecuencias Negativas / Riesgos:**
  - `XᵀX` puede ser singular si el CSV se edita con columnas dependientes; el servicio devuelve un error claro en vez de un resultado inválido.
  - El dataset es ficticio, así que las métricas demuestran correctitud del cálculo, no validez clínica. `[POR DEFINIR: validación con datos reales]`
