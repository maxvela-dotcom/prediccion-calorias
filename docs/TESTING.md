# docs/TESTING.md — Plan de Pruebas y Aseguramiento de Calidad (Etapa 8)
<!-- Willys_IA: Registro de Pruebas y Auditoría QA - Taller UAB 2026 -->
<!-- PRINCIPIO DE ETAPA 8:
     «Si el test no pasa en consola, el código no existe.»
     Las pruebas automatizadas son la evidencia objetiva de que el software cumple
     las reglas del negocio y no sufre de alucinaciones.
-->

## 1. Estrategia de Pruebas del Proyecto
Las pruebas se implementan en `tests/test_app.py` y se ejecutan directamente en la terminal mediante `pytest tests/` o `python -m unittest tests.test_app.py`. Cada prueba responde directamente a un criterio **Dado · Cuando · Entonces** del `SPEC.md`.

- Cada caso usa una **base SQLite temporal** (`setUp`), por lo que no afecta `data/app.db`. Las pruebas de regresión usan además **CSV temporales** con coeficientes conocidos (`FILAS_EXACTAS`, linealmente independientes) para verificar la ecuación normal sin depender del dataset real.
- `security.reset_rate_limits()` limpia el rate limiting en memoria entre casos.
- Las APIs JSON con sesión se prueban con el header `X-CSRF-Token` (obtenido de `/api/csrf-token` o del `<meta>` del dashboard).
- Las pruebas de SMTP/Redis **no requieren servicios externos**: validan el fallback seguro a consola y a memoria.

---

## 2. Matriz de Casos de Prueba Ejecutados (53 casos)

| ID Caso | Categoría | Escenario Probado | Salida / Comportamiento Esperado | Estado |
| :---: | :--- | :--- | :--- | :---: |
| **TC-01** | Camino Feliz | Registro exitoso de elemento MVP vía Service/Repository | ID asignado y elemento persistido | `APROBADO ✓` |
| **TC-02** | Borde / Inválido | Nombre de elemento vacío (< 3 caracteres) | `ValueError`; no altera la lista | `APROBADO ✓` |
| **TC-03** | Regla Negocio | Cantidad negativa en elemento MVP | `validar()` falso; registro bloqueado | `APROBADO ✓` |
| **TC-04** | Regla Negocio | Duplicado de elemento activo | Segundo registro rechazado | `APROBADO ✓` |
| **TC-05** | Controlador | Manejo defensivo y actualización de estado | Respuesta controlada y estado actualizado | `APROBADO ✓` |
| **TC-06** | Camino Feliz | Registro de usuario con rol, estado y hash | Usuario creado con `password_hash` (no texto plano) | `APROBADO ✓` |
| **TC-07** | Borde / Inválido | Nombre corto, correo inválido o contraseña débil | `ValueError`; usuario no creado | `APROBADO ✓` |
| **TC-08** | Regla Negocio | Correo duplicado | `ValueError`; unicidad respetada | `APROBADO ✓` |
| **TC-09** | Controlador | Errores defensivos y listado de usuarios | Sin excepciones no controladas | `APROBADO ✓` |
| **TC-10** | Integración Web | `GET /` sin sesión | Redirección a `/login` | `APROBADO ✓` |
| **TC-11** | Integración API | `POST/GET /api/mvp` | `201` al crear y listado JSON | `APROBADO ✓` |
| **TC-12** | Integración API | `POST /api/mvp` con datos inválidos | `400 Bad Request` | `APROBADO ✓` |
| **TC-13** | Integración API | Registro vía `/api/usuarios` y correo duplicado | `201` y luego `400` | `APROBADO ✓` |
| **TC-14** | Integración API | `POST /api/mvp/<id>/estado` | Estado actualizado correctamente | `APROBADO ✓` |
| **TC-15** | Cálculo / Persistencia | `MET × peso × (min/60)` y aislamiento por usuario | Cálculo exacto y persistido | `APROBADO ✓` |
| **TC-16** | Borde / Inválido | Peso/duración fuera de rango, MET inválido, actividad corta | `ValueError`; no persiste | `APROBADO ✓` |
| **TC-17** | Seguridad | `GET/POST /api/calorias` sin sesión | `401 No autenticado` | `APROBADO ✓` |
| **TC-18** | Flujo Web | Registro → sesión → dashboard → predicción (con CSRF) | Flujo completo exitoso (`201`) | `APROBADO ✓` |
| **TC-19** | Seguridad | Login inválido y POST sin CSRF | `401` y `400` respectivamente | `APROBADO ✓` |
| **TC-20** | Perfil / Catálogo | `/api/perfil` (con CSRF) y `/api/met-catalogo` | Perfil actualiza peso; catálogo disponible | `APROBADO ✓` |
| **TC-21** | Modelo ampliado | Ecuación de Keytel (M/F) y fallback a MET | Resultado Keytel exacto y `metodo_calculo` correcto | `APROBADO ✓` |
| **TC-22** | Seguridad | Rate limiting en memoria | Permite hasta el máximo, bloquea y `reset` limpia | `APROBADO ✓` |
| **TC-23** | Exportación | `GET /api/calorias/export.csv` sin sesión y con filtros | `401` sin sesión; CSV con solo registros filtrados | `APROBADO ✓` |
| **TC-24** | Verificación | Token de verificación de correo de un solo uso | Marca verificado y no puede reutilizarse | `APROBADO ✓` |
| **TC-25** | Recuperación | Reset de contraseña con token y política segura | Cambia contraseña, invalida token y rechaza débil | `APROBADO ✓` |
| **TC-26** | Seguridad | `POST /api/calorias` y `/api/perfil` sin `X-CSRF-Token` | `403`; con header, `201` | `APROBADO ✓` |
| **TC-27** | Perfil ampliado | Perfil guarda edad/sexo/FC y API usa Keytel | `KEYTEL` con datos del perfil; edad inválida `400` | `APROBADO ✓` |
| **TC-28** | Seguridad / Usuarios | Listar usuarios y dar de baja | `GET /api/usuarios` sin sesión `401`; baja sin CSRF `403`; baja propia con CSRF `200` | `APROBADO ✓` |
| **TC-29** | Persistencia | Migraciones versionadas e idempotentes | `schema_migrations` registra todas las versiones (`1–8`); reejecutar no duplica; DB antigua recibe columnas | `APROBADO ✓` |
| **TC-30** | Paginación | Historial por servicio y API con `page`/`per_page` | `total`, `total_pages`, orden reciente y suma global correctos; `per_page` máximo 100 | `APROBADO ✓` |
| **TC-31** | Seguridad | Backend de rate limiting pluggable | `memory` funciona; `redis` sin `REDIS_URL` cae a memoria; `auto` es seguro | `APROBADO ✓` |
| **TC-32** | Notificaciones | SMTP no configurado o con placeholders | Canal `consola`, enlace impreso y sin excepción | `APROBADO ✓` |
| **TC-33** | Catálogo | Metadatos de versión/fuente/revisión | API expone `catalogo.version` y 15 actividades | `APROBADO ✓` |
| **TC-34** | Explicabilidad | Desglose del cálculo en POST, listado, detalle y dashboard | `desglose` con fórmula, valores sustituidos y resultado (MET y Keytel); UI muestra «Cómo se hace el cálculo» y «Ver cálculo» | `APROBADO ✓` |
| **TC-35** | Borrado seguro | `DELETE /api/calorias/<id>` con sesión, CSRF y propiedad | Sin sesión `401`; sin CSRF `403`; otro usuario `404`; dueño `200` y registro movido a papelera | `APROBADO ✓` |
| **TC-36** | Papelera y restauración | Borrado suave, listado de papelera, detalle y restauración | Registro fuera del historial, presente en papelera con `eliminado`/`fecha_eliminacion`; restaurar sin CSRF `403`, con CSRF `200` y vuelve al historial | `APROBADO ✓` |
| **TC-37** | Borrado definitivo y vaciado | `DELETE .../<id>/definitivo`, `DELETE /api/calorias/papelera` y migración v6 | Sin sesión `401`, sin CSRF `403`, otro usuario `404`; vaciado solo afecta a la papelera propia; columnas `eliminado`/`fecha_eliminacion` presentes | `APROBADO ✓` |
| **TC-38** | Google Sign-In / Esquema | Migración v7 | Columnas `proveedor` y `google_sub` en `usuarios`, índice único `idx_usuarios_google_sub` y versión 7 registrada | `APROBADO ✓` |
| **TC-39** | Google Sign-In / UI | `/login` y `/google/login` sin credenciales | Botón «Continuar con Google» desactivado con `[POR DEFINIR]`; `/google/login` muestra aviso pendiente | `APROBADO ✓` |
| **TC-40** | Google Sign-In / Vinculación | Correo de Google ya registrado | Se vincula por `google_sub`, conserva `id`, contraseña e historial; otro `sub` no puede apropiarse del correo | `APROBADO ✓` |
| **TC-41** | Google Sign-In / Alta | Correo de Google nuevo | Crea usuario `GOOGLE` con correo verificado y contraseña aleatoria; repetir el `sub` reingresa; correo no verificado se rechaza | `APROBADO ✓` |
| **TC-42** | Google Sign-In / OAuth | `/google/login` → `/google/callback` con verificador inyectado | URL de Google con `state`; `state` inválido `400`; `state` válido abre sesión y redirige a `/dashboard` | `APROBADO ✓` |
| **TC-43** | Regresión / Dataset | `data/dataset_calorias.csv` con cabecera `X_1,X_2,X_3,X_4,Y` y 80 filas | CSV presente, 5 columnas, alturas en rango; CSV sin `Y` se rechaza con mensaje claro | `APROBADO ✓` |
| **TC-44** | Regresión / Álgebra | Ecuación normal con coeficientes conocidos | `X` 12×5 con unos, `Xᵀ` 5×12, `XᵀX` 5×5, `XᵀY` 5×1, `β` 5×1; recupera `[10, 2, 3, -1, 4]` | `APROBADO ✓` |
| **TC-45** | Regresión / Métricas | MAE, RMSE y R² con datos sin ruido y con el CSV real | Dataset exacto da MAE/RMSE 0 y R² 1; dataset real da MAE 1.3155, RMSE 1.5224, R² 0.9999 | `APROBADO ✓` |
| **TC-46** | Regresión / Serialización | `serializar()` para análisis técnico y gráficas | Dimensiones 80×5 / 5×80 / 80×1 / 5×1, ecuación simbólica y numérica, 5 interpretaciones, 3 métricas y 80+80+4 puntos de gráficas | `APROBADO ✓` |
| **TC-47** | Regresión / Esquema | Migración v8 | Columnas `altura_cm` y `modelo_snapshot` en predicciones, `altura_preferida_cm` en usuarios y versión 8 registrada | `APROBADO ✓` |
| **TC-48** | Regresión / Trazabilidad | Predicción con β y desglose histórico | `metodo_calculo='REGRESION'`, snapshot con 5 β, desglose con 5 aportes y 5 pasos; si cambia el snapshot, el desglose usa los β guardados sin alterar el resultado | `APROBADO ✓` |
| **TC-49** | Regresión / Integración | `GET /api/calorias/analisis` y sección del dashboard | Sin sesión `401`; con sesión `200` con `matrices`/`metricas`/`graficas`; HTML contiene «Análisis técnico», los 3 canvas y Chart.js local | `APROBADO ✓` |
| **TC-50** | Regresión / Flujo completo | Perfil con altura → regresión → historial, papelera y restauración | Perfil guarda 172 cm; POST usa `REGRESION` y toma la altura del perfil; borrar, listar en papelera y restaurar funcionan | `APROBADO ✓` |
| **TC-51** | Regresión / Respaldo | Sin altura se conservan Keytel y MET | `KEYTEL` con FC/edad/sexo y sin `altura_cm`; sin esos datos `MET` sin `modelo_snapshot` | `APROBADO ✓` |

---

## 3. Dinámica «Cazar la Alucinación» (Defectos Encontrados y Corregidos)
> *En esta sección el equipo registra con honestidad técnica los errores o supuestos inventados por la IA que tuvieron que corregir durante el laboratorio:*

### Alucinación / Defecto 1 Cazado
- **Qué propuso la IA:** La IA sugirió una función que aceptaba cantidades con valor `0` y nombres de un solo espacio (`" "`).
- **Por qué era incorrecto:** Violaba las reglas de negocio **RN-01** y **RN-03** del `SPEC.md`.
- **Cómo lo corrigió el equipo:** Agregamos validación estricta con `.strip()` y condición `valor > 0`, respaldada por `test_tc02` y `test_tc03`.

### Alucinación / Defecto 2 Cazado
- **Qué propuso la IA:** Endpoints JSON que aceptaban `POST` con la sola cookie de sesión, sin token anti-CSRF.
- **Por qué era incorrecto:** Un sitio externo podría ejecutar acciones en nombre del usuario autenticado.
- **Cómo lo corrigió el equipo:** Se exigió el header `X-CSRF-Token` en APIs con sesión y se agregó `test_tc26`.

### Alucinación / Defecto 3 Cazado
- **Qué propuso la IA:** Reutilizar el mismo token de verificación/recuperación indefinidamente.
- **Por qué era incorrecto:** Un enlace filtrado permitiría cambios repetidos de contraseña o verificaciones falsas.
- **Cómo lo corrigió el equipo:** Tokens de **un solo uso** con expiración (24 h / 60 min), validados por `test_tc24` y `test_tc25`.

### Alucinación / Defecto 4 Cazado
- **Qué propuso la IA:** Generar los datos de prueba de regresión con patrones modulares (`x2 = 150 + i`, `x4 = 10·i`), suponiendo que bastaba con tener 5 filas.
- **Por qué era incorrecto:** Las variables eran linealmente dependientes; `XᵀX` era singular y `np.linalg.inv` lanzaba `LinAlgError`, además de que los coeficientes recuperados no coincidían con los originales.
- **Cómo lo corrigió el equipo:** Se definió `FILAS_EXACTAS` con 12 observaciones linealmente independientes (rango 5) y se generó el dataset real de 80 filas con ruido acotado. El módulo `regresion_lineal.py` valida la inversión y devuelve un `ValueError` comprensible; `test_tc44` y `test_tc45` verifican tanto el rango como la recuperación exacta de β.

---

## 4. Evidencia de Ejecución en Consola
```bash
$ python -m unittest discover -s tests
................................................................................................
----------------------------------------------------------------------
Ran 88 tests in 78.8s

OK
```

> Los 53 de `test_app.py` incluyen 51 casos de calorías/regresión/usuarios/Google (TC-01 a TC-51) y 2 de detección de red; se suman 31 de la escuela y 4 de certificados. Para ejecutar solo el módulo principal: `python -m unittest tests.test_app` → `Ran 53 tests ... OK`.
