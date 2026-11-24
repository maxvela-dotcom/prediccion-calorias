# docs/IDEA.md — Ficha de Identificación del Problema (Etapa 0)
<!-- Willys_IA: Definición del Problema - Taller UAB 2026 -->
<!-- REGLA DE ORO: Enfoque en el dolor del usuario. Lo no confirmado se marca [POR DEFINIR]. -->

## 1. Nombre del Proyecto y Reto Elegido
- **Proyecto:** `Asistencias Escuela de Fútbol` (registro por QR, aviso de ausencias y cálculo de cobros)
- **Categoría:** `Administración educativa / Gestión deportiva`
- **Equipo Mob #:** `[POR DEFINIR]`
  - **Piloto:** `[POR DEFINIR]`
  - **Navegante / Prompter:** `[POR DEFINIR]`
  - **Arquitecto:** `[POR DEFINIR]`
  - **Auditor QA:** `[POR DEFINIR]`

> **Nota de alcance:** el repositorio conserva el dominio de ejemplo del starter kit
> (`Calorías en Rutina`). Este documento describe el reto real que se está construyendo
> encima: el módulo **Escuela**, montado en `/escuela` y aislado en sus propias tablas
> (`ef_*`) para no romper el dominio existente.

---

## 2. Diagnóstico del Dolor (Las 5 Preguntas Clave)

### 2.1 ¿Qué problema concreto se observa?
> **Respuesta:** La escuela registra la asistencia en **6 cuadernos** (una categoría por sede),
> luego transcribe todo a Excel y calcula los cobros a mano. El cierre mensual toma **2–3 horas**
> y el trabajo administrativo completo consume **24–26 horas por semana**. En el camino se pierden
> alumnos, se duplican registros y se generan cobros errados que el padre reclama.

### 2.2 ¿A quién le ocurre y quién es el beneficiario directo?
> **Respuesta:** A la administradora de una escuela de fútbol independiente con **200 alumnos**,
> **20 entrenadores**, **3 categorías** (sub-8, sub-15, sub-18) y **2 sedes**.
> Beneficiarios directos: la administradora (deja de transcribir), los entrenadores (registran en
> segundos) y los padres (reciben el aviso el mismo día y entienden su cobro).

### 2.3 ¿Cómo se resuelve manualmente hoy y qué fricciones genera?
> **Respuesta:** El entrenador pasa lista en un cuaderno; al final del mes alguien transcribe los
> 6 cuadernos a Excel, suma asistencias y calcula montos. Fricciones: trabajo duplicado, letra
> ilegible, cuadernos que no llegan, alumnos omitidos, cobros que hay que rehacer y consultas de
> padres que interrumpen la jornada.

### 2.4 ¿Con qué frecuencia ocurre?
> **Respuesta:** Cada entrenamiento (registro) y **una vez al mes** (cierre y cobro).
> El detalle de días y horarios por sede/categoría está `[POR DEFINIR]`.

### 2.5 ¿Qué evidencia confirma que el problema es real?
> **Respuesta:** Declaración de la administradora: 6 cuadernos activos, 24–26 h semanales de
> trabajo administrativo, cierre mensual de 2–3 h y reclamos recurrentes de padres por cobros.
> La medición formal de esas horas está en curso con `docs/VALIDACION_HORAS.md`
> (**2 semanas de bitácora**; aún no hay resultados cargados).

---

## 3. Matriz de Claridad (Separación Obligatoria)

| Tipo | Declaración Concreta |
| :--- | :--- |
| **Hechos Comprobados** | 1. Existen 200 alumnos, 20 entrenadores, 3 categorías y 2 sedes.<br>2. Hoy se usan 6 cuadernos (3 categorías × 2 sedes) y una planilla Excel.<br>3. El cierre mensual consume 2–3 h y el total declarado es 24–26 h/semana.<br>4. El cobro se hace por alumno y la tarifa depende de la categoría.<br>5. Un alumno con 0 asistencias en el mes no paga; con 1 o más paga la tarifa completa.<br>6. La tardanza cuenta como asistencia completa.<br>7. Los alumnos becados no pagan. |
| **Supuestos del Equipo** | 1. El entrenador puede escanear el QR del alumno con su propio teléfono.<br>2. Los padres aceptan recibir el aviso por WhatsApp enviado por la administradora.<br>3. La PC de la escuela puede quedar encendida y conectada a la misma red que los celulares (cualquier WiFi, hotspot o cable) durante el entrenamiento (servidor local del piloto).<br>4. Un alumno con 0 asistencias durante **todo** el mes sigue siendo alumno activo (no se da de baja automáticamente). |
| **Aspectos [POR DEFINIR]** | 1. Desglose real de las 24–26 h semanales por tarea (bitácora en curso).<br>2. ~~Si el padre tendrá acceso propio al sistema~~ → **decidido para la demo:** el alumno entra con su usuario y ve solo su QR, sus faltas y su cobro (solo lectura).<br>3. Cómo se registran y justifican las faltas (certificado médico, viaje, etc.).<br>4. Qué ocurre con la cuarta falta mientras el director no la aprueba.<br>5. Quién reemplaza al director si no está disponible.<br>6. Formato y numeración del comprobante de pago.<br>7. Moneda, redondeo y política de mora (el monto de referencia es 500 Bs). |

---

## 4. Resultado Esperado en 1 Sola Frase
> **Nuestra meta es:** *«Construir un MVP web donde el entrenador registre la asistencia con un QR
> o una marca manual, la administradora reciba el aviso de cada falta el mismo día y el sistema
> calcule el cobro mensual de cada alumno sin transcribir cuadernos.»*

---

## 5. Metas Medibles del Proyecto

| Meta | Situación actual | Meta aceptada | Objetivo |
| :--- | :--- | :--- | :--- |
| Horas administrativas por semana | 24–26 h | **≤ 22 h** | **≤ 18 h** |
| Reclamos de padres por mes | Recurrentes | **≤ 1** | **0** |
| Cobros errados por mes | Recurrentes | **≤ 1** | **0** |
| Tiempo de respuesta al padre | Horas o al día siguiente | **≤ 2 min** | **≤ 30 s** (sin llamada) |

> La meta de horas se valida con `docs/VALIDACION_HORAS.md` antes de comprometerla en la
> presentación final.

---

## 6. Alcance del MVP Presentable (3 funciones)

1. **Registrar asistencia** por QR o marca manual (equivalentes), con cola offline.
2. **Avisar a la administradora** de cada falta al terminar el entrenamiento.
3. **Calcular el cobro mensual** por alumno y marcarlo como pagado o pendiente.

### Entrega actual: app compartida en la red local
- **Un solo servidor en la PC** (Flask + **SQLite única** en `data/app.db`). La PC escucha en
  `0.0.0.0:5000` (HTTP) y `0.0.0.0:5443` (HTTPS); laptop, entrenadores y alumnos abren
  `https://IP_DE_LA_PC:5443/escuela` desde cualquier dispositivo de la **misma red** (cualquier
  WiFi, hotspot o cable).
- **La base arranca completamente vacía**: sin usuarios, alumnos, sesiones ni pagos demo. El primer
  arranque abre `/escuela/setup`, donde se crea el administrador y el catálogo mínimo
  (Sede Central/Sede Norte; Sub-8 400 Bs, Sub-15 500 Bs, Sub-18 600 Bs).
- **Altas desde el panel**: el administrador registra alumnos manualmente, genera su QR y puede crear
  la cuenta de acceso de cada alumno. También crea cuentas de `ADMIN`/`ENTRENADOR`, cambia contraseñas,
  agrega sedes/categorías y da de baja alumnos sin borrar su historial.
- **Login con 3 roles reales:** `ADMIN` (todo, desde laptop o celular), `ENTRENADOR` (asistencia,
  avisos y QR; **sin cobros**) y `ALUMNO` (solo lectura de su QR, faltas y cobro).
- Todos ven **los mismos datos** al instante: lo que registra un entrenador aparece en la laptop
  de la administradora y en el celular del alumno.
- El QR se genera en el servidor; la cámara usa `BarcodeDetector` (Chrome/Edge) con fallback manual.
- **HTTPS local con CA propia:** `/ca.crt` se instala una vez en cada celular para que Chrome/Edge
  permitan instalar la PWA, usar la cámara y registrar el service worker.
- **Respaldo:** el administrador descarga una copia consistente de la base desde el panel y el
  servidor guarda además una copia diaria en `data/respaldos/` al arrancar.
- **Modo local aislado** (`?modo=local`): conserva la demo anterior con IndexedDB en el celular,
  útil si no hay red. No comparte datos con la base de la PC.
- **APK de Android:** cliente WebView firmado (`android/dist/EscuelaUAB.apk`) con URL del servidor
  configurable, cámara, descargas y la CA local incluida. Se recompila sin Gradle con
  `android/build_apk.ps1`.

### Fuera del MVP actual (documentado, no implementado)
- Comprobante de pago numerado.
- Recuperaciones y límite de 3 faltas por mes.
- Aprobaciones y reportes del director.
- Becas y sanciones como flujo administrativo (el cobro sí respeta la beca ya asignada).

---

## 7. Riesgos Principales
- **Riesgo:** el escaneo QR falla en teléfonos sin cámara compatible o sin la CA instalada.
  **Mitigación:** instalar `ca.crt` una vez y usar HTTPS; si aun así falla, marca manual desde la lista
  de ausentes y entrada del código a mano.
- **Riesgo:** no hay internet en la sede. **Mitigación:** la app compartida funciona en la **LAN sin
  internet**; si además se corta la red, el modo local (`?modo=local`) sigue registrando en el celular
  y la cola en `localStorage` reintenta al volver la conexión.
- **Riesgo:** la PC servidor está apagada o el Firewall bloquea los puertos 5000/5443.
  **Mitigación:** dejarla encendida durante el entrenamiento y ejecutar `preparar_red.bat`
  (o habilitar ambos puertos en el Firewall de Windows); la consola imprime la IP y las URL exactas
  al arrancar.
- **Riesgo:** la IP de la PC cambia y el certificado deja de coincidir.
  **Mitigación:** el servidor regenera el certificado al arrancar; reinstalar `ca.crt` y actualizar la URL.
- **Riesgo:** pérdida de datos por un solo archivo SQLite.
  **Mitigación:** respaldo diario automático en `data/respaldos/`, descarga consistente desde el
  panel y copia semanal fuera de la PC.
- **Riesgo:** el ahorro de horas no se demuestra. **Mitigación:** medir con la bitácora antes de
  afirmar la reducción; si el tiempo atacable es menor a 5 h/semana, vender el proyecto por
  reducción de errores y cobros, no por horas.
