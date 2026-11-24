# docs/DATABASE.md — Modelo de Datos e Integridad Declarativa (Etapa 4)
<!-- Willys_IA: Modelo Relacional y Restricciones de Integridad - Taller UAB 2026 -->

## 1. Esquema Relacional de Entidades

```
+------------------------------------------------+        +--------------------------------------------------+
|                   USUARIO                      |        |              PREDICCION_CALORIA                  |
+------------------------------------------------+        +--------------------------------------------------+
| PK  id                  INT  AUTOINCREMENTAL   | 1    N | PK  id                 INT  AUTOINCREMENTAL      |
|     nombre_completo     VARCHAR(60)  NOT NULL  |--------| FK  usuario_id         INT  NOT NULL             |
|     email               VARCHAR(120) NOT NULL  |        |     tipo_actividad     VARCHAR(80)  NOT NULL     |
|     password_hash       VARCHAR(255) NOT NULL  |        |     peso_kg            DECIMAL(5,2) NOT NULL     |
|     rol                 VARCHAR(20)  NOT NULL  |        |     duracion_min       DECIMAL(6,2) NOT NULL     |
|     estado              VARCHAR(20)  NOT NULL  |        |     met                DECIMAL(4,2) NOT NULL     |
|     peso_preferido_kg   DECIMAL(5,2) NULL      |        |     fc_promedio        DECIMAL(5,2) NULL         |
|     edad                INT          NULL      |        |     edad               INT          NULL         |
|     sexo                VARCHAR(10)  NULL      |        |     sexo               VARCHAR(10)  NULL         |
|     fc_reposo           DECIMAL(5,2) NULL      |        |     metodo_calculo     VARCHAR(10)  NOT NULL     |
|     email_verificado    INT          NOT NULL  |        |     calorias_estimadas DECIMAL(10,2) NOT NULL    |
|     token_verificacion  VARCHAR(120) NULL      |        |     fecha_registro     TIMESTAMP    NOT NULL     |
|     token_expira        TIMESTAMP    NULL      |        |                                                  |
|     reset_token         VARCHAR(120) NULL      |        |                                                  |
|     reset_expira        TIMESTAMP    NULL      |        |                                                  |
|     fecha_registro      TIMESTAMP    NOT NULL  |        |                                                  |
| UNIQUE(email)                                  |        |                                                  |
+------------------------------------------------+        +--------------------------------------------------+
```

---

## 2. Diccionario de Datos Detallado

> **Nota de implementación:** SQLite impone a nivel de motor **PK**, **UNIQUE**, **NOT NULL** y **FK**. Las reglas de dominio indicadas como `CHECK (...)` se validan en las capas **Model/Service** antes de persistir (no se declaran como `CHECK` en el DDL para simplificar las migraciones locales).

### 2.1 USUARIO
| Atributo | Tipo de Dato | Clave | Restricción / Validación | Descripción de Negocio |
| :--- | :---: | :---: | :--- | :--- |
| `id` | Entero (`int`) | **PK** | Único, autoincremental > 0 | Identificador primario del usuario. |
| `nombre_completo` | Texto (`str`) | - | `NOT NULL`, len >= 3 | Nombre para mostrar en la plataforma. |
| `email` | Texto (`str`) | - | `NOT NULL`, `UNIQUE`, formato correo | Credencial de inicio de sesión. |
| `password_hash` | Texto (`str`) | - | `NOT NULL` | Hash seguro (nunca texto plano). |
| `rol` | Texto (`str`) | - | `NOT NULL`, catálogo permitido | Rol del usuario (ej. ESTUDIANTE). |
| `estado` | Texto (`str`) | - | `CHECK (estado IN ('ACTIVO','INACTIVO'))` | Estado de la cuenta. |
| `peso_preferido_kg` | Decimal (`float`) | - | `NULL` o validación `0 < peso <= 500` | Peso preferido del perfil; se usa como X1 en la regresión. |
| `altura_preferida_cm` | Decimal (`float`) | - | `NULL` o validación `100 <= altura <= 250` | Altura del perfil (migración 8); se usa como X2 en la regresión. |
| `edad` | Entero (`int`) | - | `NULL` o `CHECK (edad BETWEEN 10 AND 120)` | Edad usada como X3 en la regresión y en la ecuación de Keytel. |
| `sexo` | Texto (`str`) | - | `NULL` o `CHECK (sexo IN ('M','F','OTRO'))` | Sexo usado por la ecuación de Keytel (respaldo). |
| `fc_reposo` | Decimal (`float`) | - | `NULL` o `CHECK (fc_reposo BETWEEN 30 AND 220)` | Frecuencia cardíaca en reposo (ppm). |
| `email_verificado` | Entero (`int`) | - | `NOT NULL DEFAULT 0`, valores 0/1 | Indica si el correo fue verificado. |
| `token_verificacion` | Texto (`str`) | - | `NULL`, único por emisión | Token de un solo uso para verificar correo (24 h). |
| `token_expira` | Fecha/Hora (`str`) | - | `NULL` | Expiración del token de verificación. |
| `reset_token` | Texto (`str`) | - | `NULL`, único por emisión | Token de un solo uso para recuperar contraseña (60 min). |
| `reset_expira` | Fecha/Hora (`str`) | - | `NULL` | Expiración del token de recuperación. |
| `fecha_registro` | Fecha/Hora (`str`) | - | `NOT NULL` | Marca temporal de alta. |
| `proveedor` | Texto (`str`) | - | `NOT NULL DEFAULT 'LOCAL'`, valores `LOCAL`/`GOOGLE` | Origen de la cuenta. Las cuentas Google se vinculan por correo verificado. |
| `google_sub` | Texto (`str`) | - | `NULL`, índice único parcial | Identificador estable de la cuenta de Google; `NULL` en cuentas locales. |

### 2.2 PREDICCION_CALORIA
| Atributo | Tipo de Dato | Clave | Restricción / Validación | Descripción de Negocio |
| :--- | :---: | :---: | :--- | :--- |
| `id` | Entero (`int`) | **PK** | Único, autoincremental > 0 | Identificador de la predicción. |
| `usuario_id` | Entero (`int`) | **FK** | `NOT NULL`, referencia a USUARIO.id | Propietario del registro (historial personal). |
| `tipo_actividad` | Texto (`str`) | - | `NOT NULL`, len >= 3 | Actividad/rutina realizada. |
| `peso_kg` | Decimal (`float`) | - | `CHECK (peso_kg > 0)` | Peso usado para el cálculo. |
| `duracion_min` | Decimal (`float`) | - | `CHECK (duracion_min > 0)` | Duración de la rutina en minutos. |
| `met` | Decimal (`float`) | - | `CHECK (met > 0)` | Intensidad (MET) de la actividad. |
| `fc_promedio` | Decimal (`float`) | - | `NULL` o `CHECK (fc_promedio BETWEEN 30 AND 220)` | FC promedio usada por la ecuación de Keytel. |
| `edad` | Entero (`int`) | - | `NULL` o `CHECK (edad BETWEEN 10 AND 120)` | Edad usada en el cálculo. |
| `sexo` | Texto (`str`) | - | `NULL` o `CHECK (sexo IN ('M','F','OTRO'))` | Sexo usado en el cálculo. |
| `altura_cm` | Decimal (`float`) | - | `NULL` o validación `100 <= altura <= 250` (migración 8) | Altura usada como X2 en la regresión; obligatoria en registros `REGRESION`. |
| `modelo_snapshot` | Texto (`str`) | - | `NULL`; JSON con `beta` de 5 coeficientes (migración 8) | Copia de los `β` usados al predecir; permite reconstruir el desglose histórico aunque cambie el CSV. |
| `metodo_calculo` | Texto (`str`) | - | `NOT NULL DEFAULT 'MET'`, valores `MET`/`KEYTEL`/`REGRESION` | Ecuación aplicada al resultado. |
| `calorias_estimadas` | Decimal (`float`) | - | `CHECK (calorias_estimadas >= 0)` | Resultado estimado en kcal. |
| `fecha_registro` | Fecha/Hora (`str`) | - | `NOT NULL` | Fecha/hora del cálculo. |
| `eliminado` | Entero (`int`) | - | `NOT NULL DEFAULT 0`, valores 0/1 | `1` cuando el registro está en la papelera (fuera del historial activo). |
| `fecha_eliminacion` | Fecha/Hora (`str`) | - | `NULL` | Momento en que se movió a papelera; se limpia al restaurar. |

### 2.3 SCHEMA_MIGRATIONS (control de versiones)
| Atributo | Tipo de Dato | Clave | Restricción / Validación | Descripción de Negocio |
| :--- | :---: | :---: | :--- | :--- |
| `version` | Entero (`int`) | **PK** | Único, incremental | Número de migración aplicada. |
| `nombre` | Texto (`str`) | - | `NOT NULL` | Identificador legible del cambio de esquema. |
| `aplicada_en` | Fecha/Hora (`str`) | - | `NOT NULL` | Momento en que se aplicó la migración. |

Versiones actuales: `1` esquema inicial, `2` perfil ampliado, `3` tokens/método de cálculo, `4` escuela de fútbol, `5` usuarios de escuela, `6` papelera de predicciones, `7` Google Sign-In y `8` regresión lineal. Las migraciones son idempotentes y se ejecutan en orden al iniciar la aplicación.

---

## 3. Restricciones de Integridad y su Propósito
1. **PRIMARY KEY (PK):** Identifica unívocamente cada usuario y cada predicción.
2. **FOREIGN KEY (FK lógica):** `PREDICCION_CALORIA.usuario_id` debe corresponder a un usuario existente; garantiza historial por cuenta.
3. **NOT NULL:** Evita registros incompletos (credenciales, datos de rutina o resultado).
4. **UNIQUE (`email`):** Impide cuentas duplicadas con el mismo correo.
5. **Reglas de dominio (Model/Service):** Aseguran valores válidos (`peso_kg > 0`, `duracion_min > 0`, `met` 0.5–20, `calorias_estimadas >= 0`, estados y roles permitidos). Se aplican antes de persistir; SQLite no las declara como `CHECK`.
6. **Tokens de un solo uso:** `token_verificacion` y `reset_token` identifican un único registro mientras están vigentes; se limpian al consumirse.
7. **Rangos de perfil:** altura 100–250 cm, edad 10–120, sexo `M`/`F`/`OTRO`, FC de reposo y FC promedio 30–220 ppm, peso <= 500 kg. La altura es obligatoria en el servicio cuando el método es `REGRESION`.

---

## 4. Implementación en Código
- **Persistencia:** SQLite local (`src/database.py`, `data/app.db`) con creación automática de tablas (`usuarios`, `predicciones_calorias`, `elementos_mvp`) y constraints de motor (PK, UNIQUE email, FK usuario_id, NOT NULL).
- **Migraciones versionadas:** `MIGRACIONES` define versión, nombre y función aplicadora. `init_db()` ejecuta solo las pendientes y registra cada una en `schema_migrations`; las funciones usan `CREATE TABLE IF NOT EXISTS` y agregan columnas faltantes con `ALTER TABLE` para bases existentes.
- **Índice de historial:** `idx_predicciones_usuario (usuario_id, id DESC)` optimiza el listado paginado.
- **Papelera:** `eliminado`/`fecha_eliminacion` (migración 6) implementan borrado suave; las consultas filtran por `COALESCE(eliminado, 0)`. El índice `idx_predicciones_usuario_estado (usuario_id, eliminado, id DESC)` acelera historial y papelera. Restaurar vuelve a `0`; el borrado definitivo elimina la fila solo desde la papelera.
- **Google Sign-In:** `proveedor`/`google_sub` (migración 7) permiten autenticación opcional con Google. El índice parcial `idx_usuarios_google_sub (google_sub) WHERE google_sub IS NOT NULL` impide duplicar el identificador de una cuenta de Google.
- **Regresión lineal:** `predicciones_calorias.altura_cm` y `modelo_snapshot`, y `usuarios.altura_preferida_cm` (migración 8). El CSV `data/dataset_calorias.csv` no se almacena en SQLite: solo se persiste el resultado y los coeficientes usados.
- **Capas:** `@dataclass` en modelos + validaciones en Model/Service + repositorios SQL (`usuario_repository.py`, `caloria_repository.py`, `mvp_repository.py`).
- **Perfil:** `usuarios.peso_preferido_kg`, `altura_preferida_cm`, `edad`, `sexo` y `fc_reposo` gestionados por el servicio/API de perfil.
- **Trazabilidad:** cada predicción guarda `metodo_calculo`, los parámetros (`altura_cm`, `fc_promedio`, `edad`, `sexo`) y el `modelo_snapshot` con los `β` exactos usados en el desglose.
- **Pendiente:** `[POR DEFINIR]` adaptación a PostgreSQL/ORM y migraciones de producción para entornos multiusuario.

