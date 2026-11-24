# docs/VALIDACION_HORAS.md — Instrumento de Validación del Punto (a)

> **Proyecto:** Sistema de registro y control de asistencias — Escuela de Fútbol
> **Etapa:** Validación previa a `RESEARCH.md` y `SPEC.md`
> **Objetivo:** Medir en qué se van realmente las 24–26 horas semanales declaradas por la escuela.
> **Regla de oro:** Sin tecnología. Papel, Excel o bloc de notas. No se escribe código en esta etapa.

---

## 1. Qué queremos demostrar o refutar

| Hipótesis | Cómo se confirma | Cómo se refuta |
|---|---|---|
| La mayor parte del tiempo se va en **registrar, transcribir y corregir asistencia** | Esas 3 categorías suman **más del 50 %** de las horas | Suma menos del 50 % |
| El **cierre mensual** es solo una parte pequeña del problema | El cierre pesa **menos del 20 %** del total mensual | Pesa más |
| Las **consultas de padres** consumen tiempo real | Hay **más de 10 consultas por semana** y promedian 5–7 min | Son pocas y breves |
| Los **errores** son esporádicos | 3 o más incidentes registrados en 2 semanas | Menos de 3 |

---

## 2. Método: bitácora de 2 semanas

- **Semana 1:** una semana normal.
- **Semana 2:** la que incluya el **cierre de mes**.

Reglas para que el dato sirva:

1. Se anota **en el momento**, no al final del día.
2. Se registra en bloques de **15 minutos como mínimo**.
3. **No se redondea hacia abajo** ni se omiten las interrupciones.
4. Se anota también lo que **no** es del proyecto, para poder separarlo.
5. Lo llena **la misma persona** que hoy hace el trabajo: el administrador.

---

## 3. Formato de la bitácora

| Fecha | Inicio | Fin | Min | Categoría | Sede | Detalle (qué hizo) |
|---|---|---|---|---|---|---|
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |

**Categorías:**

| # | Categoría | Ejemplos |
|---|---|---|
| 1 | **Registro de asistencia** | Pasar lista, llenar cuaderno, retomar lista al final |
| 2 | **Transcripción y consolidación** | Pasar cuadernos a Excel, sumar, cerrar el mes |
| 3 | **Cobro y comprobantes** | Calcular montos, llenar talonario, cobrar, firmar |
| 4 | **Consultas de padres** | Llamadas, WhatsApp, reclamos, explicaciones |
| 5 | **Corrección de errores** | Rehacer listas, resolver duplicados, aclarar cobros |
| 6 | **Otras tareas administrativas** | Inscripciones, horarios, compras, limpieza, etc. |

> La categoría **6** es clave: si es la más grande, el problema no es la asistencia y hay que replantear el proyecto.

---

## 4. Registro de incidentes (hoja aparte)

Cada vez que algo sale mal, una línea:

| Fecha | Tipo | Minutos perdidos | Personas involucradas | Costo estimado (Bs) |
|---|---|---|---|---|
| | Cuaderno perdido / doble registro / alumno omitido / cobro errado / reclamo de padre | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |

Esto valida los "2 al mes" y permite calcular el costo real del error.

---

## 5. Contador de consultas de padres (hoja aparte)

| Fecha | Medio (llamada / WhatsApp / presencial) | Minutos | Motivo | ¿Se resolvió en el momento? |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |

Sirve para comprobar los **5–7 minutos** y para saber si la meta de **≤ 2 minutos** es realista.

---

## 6. Preguntas de cierre de cada día (2 minutos)

1. ¿Cuál fue la tarea que **más tiempo** me quitó hoy?
2. ¿Qué **error** tuve que corregir hoy?
3. ¿Cuántos **padres** me consultaron hoy?
4. ¿Qué hice hoy que **no debería** estar haciendo yo?

---

## 7. Cómo se analiza al final

### Paso 1 — Suma por categoría

| Categoría | Horas en 2 semanas | % del total |
|---|---|---|
| 1. Registro | | |
| 2. Transcripción | | |
| 3. Cobro | | |
| 4. Consultas | | |
| 5. Corrección | | |
| 6. Otras | | |
| **Total** | | 100 % |

### Paso 2 — Horas semanales reales

Divide el total entre 2 y compáralo con las **24–26 h** declaradas.

### Paso 3 — Tiempo atacable por el sistema

```text
Tiempo atacable = Categoría 1 + Categoría 2 + Categoría 5 + 50 % de Categoría 3
```

Las consultas (4) **no** las elimina el sistema: el padre seguirá llamando, solo que con mejor información. Y "otras" (6) queda intacta.

### Paso 4 — Proyección con reducción conservadora del 60 %

```text
Horas proyectadas = Horas actuales − (Tiempo atacable × 0,60)
```

### Ejemplo con números inventados (solo para mostrar el cálculo)

Supón que en 2 semanas salen 48 h, es decir 24 h/semana, repartidas así:

| Categoría | Horas/semana |
|---|---|
| 1. Registro | 4 |
| 2. Transcripción | 5 |
| 3. Cobro | 6 |
| 4. Consultas | 5 |
| 5. Corrección | 3 |
| 6. Otras | 1 |
| **Total** | **24** |

- Tiempo atacable = 4 + 5 + 3 + 3 = **15 h**
- Reducción al 60 % = **9 h**
- Proyección = 24 − 9 = **15 h/semana**

Con eso se cumpliría el objetivo (≤ 18 h) y sobraría margen. Si en cambio el atacable fuera solo 4 h, la proyección daría 21,6 h: se roza el mínimo y el proyecto queda en duda.

---

## 8. Criterio de decisión

| Resultado | Qué hacer |
|---|---|
| Tiempo atacable **≥ 10 h/semana** | El proyecto se justifica. Pasar a `RESEARCH.md` y `SPEC.md`. |
| Tiempo atacable **entre 5 y 10 h** | Se justifica, pero hay que ajustar la meta de horas o ampliar el alcance (comprobantes, recuperaciones). |
| Tiempo atacable **< 5 h** | **No** se justifica por ahorro de tiempo. Habría que venderlo por reducción de errores y cobros, no por horas. |

---

## 9. Cuándo detenerse

Con **5 días hábiles registrados**, **3 incidentes** y **10 consultas** ya hay suficiente para decidir. No hace falta un mes.

---

## 10. Advertencia metodológica

Si el administrador llena esto mientras hace su trabajo, el registro mismo le quitará tiempo y podría **inflar** las horas. Por eso conviene que lo llene durante **10–15 minutos al final de cada bloque**, no al final del día, y que alguien más revise los totales.

---

## 11. Datos que deben quedar al terminar

- [ ] Horas semanales reales medidas (no declaradas).
- [ ] Porcentaje de tiempo por categoría.
- [ ] Número de incidentes en 2 semanas y su costo estimado.
- [ ] Número de consultas de padres y su duración promedio.
- [ ] Tiempo atacable calculado.
- [ ] Proyección de horas con reducción del 60 %.
- [ ] Decisión: **seguir / ajustar alcance / replantear**.

---

*Documento de validación previa. No forma parte de las 10 etapas de la Guía Metodológica, pero alimenta directamente `docs/IDEA.md`, `docs/RESEARCH.md` y `docs/SPEC.md`.*
