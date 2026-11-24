# docs/EVALUATION.md — Evaluación Crítica y Balance Técnico (Etapa 9)
<!-- Willys_IA: Evaluación del MVP y Balance de Aprendizaje - Taller UAB 2026 -->
<!-- PRINCIPIO DE ETAPA 9:
     «Honestidad Intelectual y Académica.»
     Un ingeniero profesional no esconde los defectos de su software; audita con claridad
     qué se logró, qué quedó pendiente (deuda técnica) y qué aportó el criterio humano.
-->

## 1. Grado de Cumplimiento contra el Contrato (SPEC.md)

| Requisito / Función | Estado de Implementación | Observación Técnica |
| :--- | :---: | :--- |
| **RF-01: Cuenta y acceso** | `100% CUMPLIDO ✓` | Registro/login/logout con hash `werkzeug.security`, política de contraseña y sesión Flask. |
| **RF-02: Predicción de calorías** | `100% CUMPLIDO ✓` | Regresión lineal múltiple entrenada desde CSV con `β = (XᵀX)⁻¹XᵀY`; respaldo MET/Keytel; `metodo_calculo`, parámetros y `modelo_snapshot` persistidos para trazabilidad. |
| **RF-03: Historial personal y exportación** | `100% CUMPLIDO ✓` | `GET /api/calorias` paginado con filtros, KPIs en dashboard y `GET /api/calorias/export.csv` (incluye altura). |
| **RF-04: Perfil ampliado** | `100% CUMPLIDO ✓` | `peso_preferido_kg`, `altura_preferida_cm`, `edad`, `sexo`, `fc_reposo` validados y persistidos en SQLite. |
| **RF-07: Análisis técnico visible** | `100% CUMPLIDO ✓` | Dataset/estadísticos, matrices con dimensiones, ecuación e interpretación de `β`, MAE/RMSE/R² y 3 gráficas en `/dashboard`; JSON en `/api/calorias/analisis`. |
| **RF-05: Verificación y recuperación** | `100% CUMPLIDO ✓` | Tokens de un solo uso (24 h / 60 min); SMTP opcional con fallback a consola. |
| **RNF-03: Seguridad** | `100% CUMPLIDO ✓` | CSRF en formularios y APIs JSON, rate limiting pluggable, cookies `HttpOnly`/`SameSite=Lax`. |
| **Persistencia evolutiva** | `100% CUMPLIDO ✓` | Migraciones versionadas e idempotentes en `schema_migrations`, compatibles con DB existentes. |
| **Pruebas Automatizadas** | `100% CUMPLIDO ✓` | **53 casos** (TC-01 a TC-51) en verde con `python -m unittest tests.test_app`; **88** con `python -m unittest discover -s tests`. |

---

## 2. Deuda Técnica Declarada (Lo que quedó pendiente conscientemente)
1. **Envío de correo institucional:** el envío SMTP ya es opcional, pero faltan proveedor/credenciales y plantillas oficiales. `[POR DEFINIR: SMTP institucional y plantillas]`
2. **Rate limiting distribuido en producción:** el backend Redis existe; falta desplegarlo y definir proxy/infraestructura. `[POR DEFINIR: Redis gestionado y despliegue]`
3. **PostgreSQL:** SQLite local sigue siendo el motor del MVP; las migraciones versionadas son propias de SQLite. `[POR DEFINIR: PostgreSQL/ORM y migraciones de producción]`
4. **Validez clínica del modelo:** la regresión ya entrena desde un CSV y reporta MAE 1.3155 / RMSE 1.5224 / R² 0.9999, pero el dataset es ficticio y anonimizado; las métricas verifican el cálculo, no la precisión médica. `[POR DEFINIR: dataset real y validación profesional]`
5. **Autenticación de clientes externos:** el MVP usa sesión Flask; no hay JWT/OAuth. Google Sign-In es opcional y sigue sin credenciales reales (`[POR DEFINIR]`). `[POR DEFINIR: política de tokens para terceros]`

---

## 3. Balance del Aporte de la IA vs Criterio Humano

### ¿Qué aceleró la IA agéntica?
- Generó el andamiaje de las cuatro capas, los Blueprints Flask y la suite de pruebas.
- Redujo el tiempo de escritura de sintaxis repetitiva (SQL, validaciones, plantillas HTML).

### ¿Qué tuvo que decidir y corregir el equipo humano?
- **El equipo definió el dolor real:** La IA no sabía qué problema tenía la comunidad universitaria ni qué reglas de negocio eran prioritarias; eso provino de `docs/IDEA.md`.
- **El equipo auditó el diff:** Rechazamos dependencias innecesarias y exigimos mantener SQLite local sin servicios externos.
- **El equipo verificó la verdad del software:** La confianza en el sistema no vino de la respuesta del modelo, sino de la consola ejecutando las 53 pruebas (88 en la suite completa) y del smoke test del flujo completo, incluido el recálculo de β desde el CSV.
- **El equipo corrigió supuestos:** se rechazaron endpoints JSON sin CSRF y tokens reutilizables; durante la regresión se detectaron datasets modulares que hacían singular `XᵀX` y se corrigió el dataset con 80 filas linealmente independientes (ver `docs/TESTING.md`, sección 3).

---

## 4. Guion del Pitch de Demostración en Vivo (3 Minutos)
- **Minuto 1 (Analista / Arquitecto):** Presenta el dolor real (`docs/IDEA.md`), el reto seleccionado y cómo diseñaron el contrato (`docs/SPEC.md`).
- **Minuto 2 (Piloto / Desarrollador):** Ejecuta `python src/main.py`, crea una cuenta, inicia sesión, completa el perfil (altura/edad/sexo/FC) y registra una rutina mostrando el desglose de la **regresión** (`β`, vector `x`, aportes y resultado), la paginación del historial, la papelera y la exportación CSV.
- **Minuto 3 (Auditor QA):** Abre el **Análisis técnico** del dashboard para mostrar `X`, `Xᵀ`, `XᵀX`, `XᵀY`, `β`, las dimensiones, la interpretación de coeficientes, MAE/RMSE/R² y las 3 gráficas; luego ejecuta `python -m unittest discover -s tests` y muestra las 88 pruebas en verde junto a las alucinaciones cazadas y corregidas.
