# docs/RESEARCH.md — Investigación de Soluciones Existentes (Etapa 1)
<!-- Willys_IA: Plantilla Oficial de Investigación - Taller UAB 2026 -->
<!-- INSTRUCCIÓN RÁPIDA:
     1. Investigar no es copiar: es ver qué funciona en el mercado y qué podemos hacer mejor.
     2. Analicen al menos DOS (2) sistemas reales (comerciales o proyectos Open Source en GitHub).
     3. Anoten 3 aprendizajes que cambien o mejoren el diseño de su MVP.
     4. Distingan Hecho (dato comprobable) vs Opinión (reseña de usuario) vs Inferencia (deducción del equipo).
-->

## 1. Solución Existente 1
- **Nombre del Sistema / App:** `[Ej. OpenEMR / Trello / OpenFoodNetwork / CiviCRM]`
- **Enlace de referencia:** `https://...`
- **Público al que atiende:** `[Ej. Organizaciones sin fines de lucro, pequeñas empresas]`
- **Funcionalidades principales:**
  - `Función A:` [Descripción breve]
  - `Función B:` [Descripción breve]
- **Aspectos positivos destacados:** [Qué resuelven de forma elegante]
- **Limitaciones o quejas documentadas:** [Por qué es complejo, caro o difícil de usar]
- **Oportunidad para nuestro MVP:** [Qué podemos adaptar de forma simple]

---

## 2. Solución Existente 2
- **Nombre del Sistema / App:** `[Ej. Excel / Google Sheets con macros / App comunitaria]`
- **Enlace de referencia:** `https://...`
- **Público al que atiende:** `[Ej. Voluntarios de iglesia, secretaría]`
- **Funcionalidades principales:**
  - `Función A:` [Descripción breve]
- **Aspectos positivos destacados:** [Fácil de adoptar inicialmente]
- **Limitaciones o quejas documentadas:** [Cero validaciones de integridad, duplicados accidentales, fórmulas borradas]
- **Oportunidad para nuestro MVP:** [Automatizar las validaciones inviolables en código]

---

## 3. Matriz Crítica: Hechos vs Opiniones vs Inferencias

| Declaración | Clasificación | Justificación |
| :--- | :---: | :--- |
| *«La plataforma X exporta reportes en formato CSV»* | **Hecho** | Verificado directamente en la documentación técnica oficial. |
| *«Un usuario comentó en un foro que la interfaz es confusa»* | **Opinión** | Es la percepción subjetiva de una persona; no se generaliza. |
| *«Como no tiene app móvil para Android, seguro que nadie la usa»* | **Inferencia** | Deducción del equipo que debe contrastarse con datos reales. |

---

## 4. Los Tres (3) Aprendizajes Clave para Nuestro Proyecto
1. **Aprendizaje 1 (Funcionalidad):** *[Ej. Comprobamos que tener un campo de "Estado" predeterminado evita que las solicitudes se queden en el limbo.]*
2. **Aprendizaje 2 (Simplicidad):** *[Ej. Los sistemas comerciales fallan porque piden 25 campos obligatorios; nuestro MVP solo pedirá 4 campos esenciales.]*
3. **Aprendizaje 3 (Arquitectura/Datos):** *[Ej. Debemos impedir llaves duplicadas desde el modelo de datos para que no se corrompa el inventario.]*

