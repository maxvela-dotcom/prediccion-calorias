# docs/TECH_STACK.md — Selección Tecnológica y Viabilidad (Etapa 6)
<!-- Willys_IA: Justificación Técnica del Stack - Taller UAB 2026 -->
<!-- PRINCIPIO DE ETAPA 6:
     «No elijas tecnología por moda; elígela por viabilidad, robustez y conocimiento del equipo.»
-->

## 1. Stack Tecnológico Seleccionado para el Taller

| Componente | Tecnología Elegida | Justificación Técnica |
| :--- | :--- | :--- |
| **Lenguaje Principal** | **Python 3.10+** | Lenguaje estándar de formación en UAB, sintaxis limpia, tipado moderno (`typing`) y ejecución inmediata. |
| **Servidor y API Web** | **Flask 3.x** | Microframework ligero, intuitivo y pedagógico; arquitectura con Blueprints idéntica a Spring Boot. |
| **Interfaz de Usuario** | **HTML5 + CSS Moderno + Chart.js local** | Dashboard responsivo de una sola página sin Node/npm; Chart.js se sirve desde `src/static/chart.umd.min.js` para graficar sin Internet. |
| **Álgebra lineal** | **NumPy 1.26+** | Única dependencia añadida para el modelo: construye `X`, `Xᵀ`, `XᵀX`, `XᵀY` y resuelve `β = (XᵀX)⁻¹XᵀY` de forma explícita, sin frameworks de ML. |
| **Arquitectura Interna** | **Monolito Modular en Capas** | Separación estricta de 4 capas: Controller/Blueprint -> Service -> Repository -> Model (Willys_IA). |
| **Persistencia** | **SQLite 3 (local)** | Base de datos embebida sin servidor; esquema en `src/database.py`, archivo `data/app.db`, migraciones versionadas en `schema_migrations`. |
| **Seguridad** | **Werkzeug Security + sesión Flask** | Hash de contraseñas, CSRF por token de sesión/header, rate limiting pluggable (memoria/Redis) y cookies `HttpOnly`/`SameSite=Lax`. |
| **Identidad opcional** | **Google Sign-In + google-auth** | Authorization Code con `state`, verificación del ID token en servidor; se activa solo con credenciales de Google Cloud. |
| **Framework de Pruebas** | **unittest / pytest** | **53 pruebas** en `test_app.py` (88 en la suite completa) que combinan Unit Tests de capas y de regresión con Integration Tests sobre el cliente Flask (`test_client`). |
| **Entorno de Ejecución** | **Local (Virtualenv)** | Despliegue en 3 comandos (`python -m venv .venv; pip install -r requirements.txt; python src/main.py`). |
| **Gobernanza de IA** | **AGENT_RULES.md** | Archivo de reglas de ingeniería para guiar a Google Antigravity IDE, Claude Code o Cursor bajo estándar `Willys_IA`. |

---

## 2. Los Cuatro (4) Criterios de Selección Aplicados

1. **Compatibilidad con el Contrato:** Python soporta directamente las clases de datos (`@dataclass`), tipado y validaciones exigidas en `SPEC.md` y `DATABASE.md`.
2. **Conocimiento del Equipo:** Los estudiantes de segundo y tercer semestre ya dominan las estructuras de control básicas de Python, lo que les permite auditar el código generado por la IA en vez de actuar como usuarios pasivos.
3. **Viabilidad en Tiempo (4 Horas):** El entorno base se levanta en menos de 60 segundos. Descartamos dependencias pesadas que suelen fallar en laboratorios con proxies o permisos restringidos.
4. **Costo Cero y Código Abierto:** Herramientas 100% libres de licencias comerciales.

---

## 3. Hoja de Ruta Tecnológica para Semestres Superiores (Evolución)
- **Persistencia Empresarial:** Migración a **PostgreSQL** mediante SQLAlchemy / Spring Boot (Java). `[POR DEFINIR: Alembic/equivalente para producción]`
- **Correo real:** Integración SMTP institucional para verificación y recuperación; el código ya soporta SMTP opcional con fallback. `[POR DEFINIR: proveedor y plantillas]`
- **Escalabilidad de seguridad:** rate limiting distribuido con Redis (backend ya implementado) y CSRF/sesiones compartidas.
- **Frontend Moderno:** Conexión con **Angular** mediante endpoints REST JSON.
- **Auditoría Continua:** Integración de pipelines CI/CD con ejecución automática de pruebas en GitHub Actions o GitLab CI.

