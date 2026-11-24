# ESPECIFICACIÓN DE PROYECTO: [NOMBRE_DEL_SISTEMA]
<!-- Willys_IA: Plantilla de Requerimientos para Desarrollo Asistido con IA -->
<!-- Elige tu proyecto del Catálogo UAB:
     Estudiantes: TeamUp, EduMentor IA, CodeCoach, QuizLab, MiRuta
     Docentes: DocuMentor, EvalúaIA, RetroAula, PlanificaIA, AulaInsights
     Hermandad y Comunidad: ConectaAyuda, TeamUp Comunidad, EscuelaBiblia IA, AgendaComunidad, BancoSolidario, Memoria Hermandad
-->

## 1. Problema y Beneficiario [BÁSICO - OBLIGATORIO EN TALLER]
- **Nombre del Proyecto elegido:** [Ej. CodeCoach, EscuelaBiblia IA, ConectaAyuda]
- **¿Quién es el beneficiario principal?:** [Ej. Estudiante UAB, Maestro de Escuela Sabática, Docente]
- **Problema actual que resolvemos:** [Descripción breve del proceso manual, desordenado o lento]
- **Propuesta de valor:** [Qué resuelve este software en 1 sola frase clara]

## 2. Entradas, Lógica y Salidas de Datos [BÁSICO - OBLIGATORIO EN TALLER]
- **Datos de entrada:** 
  - `campo_1`: [Tipo de dato: texto, número, fecha]
  - `campo_2`: [Tipo de dato]
- **Reglas del Negocio Inviolables (Validaciones):**
  - Regla 1: [Ej. No se permiten valores numéricos menores a cero]
  - Regla 2: [Ej. No se permiten registros duplicados con el mismo identificador]
- **Salida esperada:** [Formato del resultado en pantalla de consola o reporte]

## 3. Alcance del MVP (Producto Mínimo Viable) [BÁSICO - OBLIGATORIO EN TALLER]
- **LO QUE SÍ HACE HOY (Máximo 3 funciones indispensables):**
  1. [Función 1: Registrar nuevo elemento]
  2. [Función 2: Listar / Consultar elementos registrados]
  3. [Función 3: Calcular un resumen, promedio o total]
- **LO QUE QUEDA EXCLUIDO (Para mantener foco y no desenfocarse):**
  - No hay login con contraseña encriptada.
  - No hay base de datos remota en la nube.
  - No hay interfaz web ni conexión con pasarelas de pago.

## 4. Criterios de Aceptación y Pruebas [BÁSICO - OBLIGATORIO EN TALLER]
- **Prueba Feliz (Happy Path):** Con datos válidos, el sistema debe responder: `[Respuesta esperada]`
- **Prueba de Borde (Edge Case):** Si se ingresa texto vacío o datos inválidos, el sistema debe: `[Mensaje de advertencia sin detener la ejecución]`

---

## 5. SECCIÓN AVANZADA [PARA PRÓXIMOS SEMESTRES - OPCIONAL]
<!-- Esta sección se deja preparada para cuando el estudiante curse materias de Base de Datos e Ingeniería de Software -->
- **Persistencia futura:** Migración de archivo local a PostgreSQL / SQLite.
- **Exposición de API:** Endpoints REST utilizando FastAPI o Flask.
- **Autenticación:** Roles de usuario (Administrador, Operador, Consulta).

