# -*- coding: utf-8 -*-
"""
Infraestructura de base de datos SQLite (Willys_IA).
Persistencia local para el MVP: usuarios, predicciones y módulo MVP base.

Migraciones versionadas:
- Cada cambio de esquema se registra en la tabla `schema_migrations`.
- Las migraciones son idempotentes para ser compatibles con bases existentes.
- No requieren dependencias externas (aplican con sqlite3 estándar).
"""

import os
import sqlite3
from datetime import datetime
from typing import Callable, Dict, List, Optional, Sequence, Tuple

_DB_PATH: Optional[str] = None


def configurar_db(path: str) -> None:
    global _DB_PATH
    _DB_PATH = path


def obtener_ruta_db() -> str:
    if _DB_PATH:
        return _DB_PATH
    # En la nube se puede montar un disco persistente fuera del repo sin
    # tapar data/dataset_calorias.csv (que sí se sube a Git).
    externa = (os.environ.get("DATABASE_PATH") or "").strip()
    if externa:
        ruta = os.path.abspath(externa)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        return ruta
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "app.db")


def get_connection(path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or obtener_ruta_db())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ----------------------------------------------------------------------
# Utilidades de migración
# ----------------------------------------------------------------------

def _agregar_columnas(
    cur: sqlite3.Cursor, tabla: str, columnas: Sequence[Tuple[str, str]]
) -> None:
    """Agrega columnas faltantes sin fallar si ya existen (DB antiguas)."""
    existentes = {fila[1] for fila in cur.execute(f"PRAGMA table_info({tabla})").fetchall()}
    for columna, tipo in columnas:
        if columna not in existentes:
            cur.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")


def _migracion_001_esquema_inicial(conn: sqlite3.Connection) -> None:
    """Crea las tablas base del MVP (idempotente con CREATE IF NOT EXISTS)."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_completo TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'ESTUDIANTE',
            estado TEXT NOT NULL DEFAULT 'ACTIVO',
            fecha_registro TEXT NOT NULL,
            peso_preferido_kg REAL,
            altura_preferida_cm REAL,
            edad INTEGER,
            sexo TEXT,
            fc_reposo REAL,
            email_verificado INTEGER NOT NULL DEFAULT 0,
            token_verificacion TEXT,
            token_expira TEXT,
            reset_token TEXT,
            reset_expira TEXT,
            proveedor TEXT NOT NULL DEFAULT 'LOCAL',
            google_sub TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS predicciones_calorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            tipo_actividad TEXT NOT NULL,
            peso_kg REAL NOT NULL,
            duracion_min REAL NOT NULL,
            met REAL NOT NULL,
            fc_promedio REAL,
            edad INTEGER,
            sexo TEXT,
            metodo_calculo TEXT NOT NULL DEFAULT 'MET',
            calorias_estimadas REAL NOT NULL,
            altura_cm REAL,
            modelo_snapshot TEXT,
            fecha_registro TEXT NOT NULL,
            eliminado INTEGER NOT NULL DEFAULT 0,
            fecha_eliminacion TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS elementos_mvp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria_rubro TEXT NOT NULL,
            estado TEXT NOT NULL,
            valor_numerico REAL NOT NULL,
            fecha_creacion TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_predicciones_usuario
        ON predicciones_calorias (usuario_id, id DESC)
        """
    )


def _migracion_002_perfil_ampliado(conn: sqlite3.Connection) -> None:
    """Agrega las columnas de perfil a instalaciones anteriores."""
    _agregar_columnas(
        conn.cursor(),
        "usuarios",
        [
            ("peso_preferido_kg", "REAL"),
            ("edad", "INTEGER"),
            ("sexo", "TEXT"),
            ("fc_reposo", "REAL"),
        ],
    )


def _migracion_003_tokens_y_metodo(conn: sqlite3.Connection) -> None:
    """Agrega verificación/reset de cuenta y trazabilidad del método de cálculo."""
    cur = conn.cursor()
    _agregar_columnas(
        cur,
        "usuarios",
        [
            ("email_verificado", "INTEGER NOT NULL DEFAULT 0"),
            ("token_verificacion", "TEXT"),
            ("token_expira", "TEXT"),
            ("reset_token", "TEXT"),
            ("reset_expira", "TEXT"),
        ],
    )
    _agregar_columnas(
        cur,
        "predicciones_calorias",
        [
            ("fc_promedio", "REAL"),
            ("edad", "INTEGER"),
            ("sexo", "TEXT"),
            ("metodo_calculo", "TEXT NOT NULL DEFAULT 'MET'"),
        ],
    )


def _migracion_004_escuela_futbol(conn: sqlite3.Connection) -> None:
    """
    Willys_IA: Crea el esquema del módulo Escuela de Fútbol.
    Tablas con prefijo `ef_` para no colisionar con el dominio de calorías.
    Reglas de integridad: PK, FK, UNIQUE y CHECK declarativos.
    """
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ef_sedes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ef_categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            precio_mensual REAL NOT NULL CHECK (precio_mensual > 0)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ef_estudiantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria_id INTEGER NOT NULL,
            sede_id INTEGER NOT NULL,
            qr_token TEXT NOT NULL UNIQUE,
            becado INTEGER NOT NULL DEFAULT 0 CHECK (becado IN (0, 1)),
            estado TEXT NOT NULL DEFAULT 'ACTIVO'
                CHECK (estado IN ('ACTIVO', 'INACTIVO')),
            fecha_registro TEXT NOT NULL,
            FOREIGN KEY(categoria_id) REFERENCES ef_categorias(id),
            FOREIGN KEY(sede_id) REFERENCES ef_sedes(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ef_sesiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sede_id INTEGER NOT NULL,
            categoria_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            entrenador TEXT NOT NULL,
            creada_en TEXT NOT NULL,
            UNIQUE(sede_id, categoria_id, fecha, hora),
            FOREIGN KEY(sede_id) REFERENCES ef_sedes(id),
            FOREIGN KEY(categoria_id) REFERENCES ef_categorias(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ef_asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id INTEGER NOT NULL,
            estudiante_id INTEGER NOT NULL,
            metodo TEXT NOT NULL DEFAULT 'QR'
                CHECK (metodo IN ('QR', 'MANUAL')),
            registrada_en TEXT NOT NULL,
            UNIQUE(sesion_id, estudiante_id),
            FOREIGN KEY(sesion_id) REFERENCES ef_sesiones(id),
            FOREIGN KEY(estudiante_id) REFERENCES ef_estudiantes(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ef_avisos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id INTEGER NOT NULL,
            estudiante_id INTEGER NOT NULL,
            estado TEXT NOT NULL DEFAULT 'PENDIENTE'
                CHECK (estado IN ('PENDIENTE', 'ENVIADA')),
            creada_en TEXT NOT NULL,
            enviada_en TEXT,
            UNIQUE(sesion_id, estudiante_id),
            FOREIGN KEY(sesion_id) REFERENCES ef_sesiones(id),
            FOREIGN KEY(estudiante_id) REFERENCES ef_estudiantes(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ef_pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id INTEGER NOT NULL,
            periodo TEXT NOT NULL,
            monto REAL NOT NULL CHECK (monto >= 0),
            estado TEXT NOT NULL DEFAULT 'PENDIENTE'
                CHECK (estado IN ('PAGADO', 'PENDIENTE')),
            fecha_pago TEXT,
            UNIQUE(estudiante_id, periodo),
            FOREIGN KEY(estudiante_id) REFERENCES ef_estudiantes(id)
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ef_estudiantes_sede_categoria
        ON ef_estudiantes (sede_id, categoria_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ef_asistencias_sesion
        ON ef_asistencias (sesion_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ef_sesiones_fecha
        ON ef_sesiones (fecha)
        """
    )


def _migracion_005_usuarios_escuela(conn: sqlite3.Connection) -> None:
    """
    Willys_IA: usuarios de la app compartida de Escuela (admin, entrenador, alumno).
    Los usuarios y roles se guardan en SQLite, igual que el resto del módulo.
    """
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ef_usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL CHECK (rol IN ('ADMIN', 'ENTRENADOR', 'ALUMNO')),
            estudiante_id INTEGER,
            activo INTEGER NOT NULL DEFAULT 1,
            fecha_creacion TEXT NOT NULL,
            FOREIGN KEY(estudiante_id) REFERENCES ef_estudiantes(id)
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ef_usuarios_rol
        ON ef_usuarios (rol)
        """
    )


def _migracion_006_papelera_predicciones(conn: sqlite3.Connection) -> None:
    """
    Willys_IA: papelera de predicciones.

    `eliminado = 1` conserva el registro fuera del historial activo; la
    restauración vuelve a ponerlo a `0`. Las consultas filtran por esta columna.
    """
    cur = conn.cursor()
    _agregar_columnas(
        cur,
        "predicciones_calorias",
        [
            ("eliminado", "INTEGER NOT NULL DEFAULT 0"),
            ("fecha_eliminacion", "TEXT"),
        ],
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_predicciones_usuario_estado
        ON predicciones_calorias (usuario_id, eliminado, id DESC)
        """
    )


def _migracion_007_google_signin(conn: sqlite3.Connection) -> None:
    """
    Willys_IA: Google Sign-In como proveedor de identidad opcional.

    `proveedor` distingue cuentas locales de cuentas vinculadas a Google y
    `google_sub` guarda el identificador estable de la cuenta de Google. El
    índice parcial evita que un mismo `sub` se asocie a dos usuarios.
    """
    cur = conn.cursor()
    _agregar_columnas(
        cur,
        "usuarios",
        [
            ("proveedor", "TEXT NOT NULL DEFAULT 'LOCAL'"),
            ("google_sub", "TEXT"),
        ],
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_google_sub
        ON usuarios (google_sub) WHERE google_sub IS NOT NULL
        """
    )


def _migracion_008_regresion_lineal(conn: sqlite3.Connection) -> None:
    """
    Willys_IA: regresión lineal múltiple y predictores del perfil.

    `altura_cm` completa los cuatro predictores del CSV en cada predicción y
    `modelo_snapshot` guarda una copia de β para reconstruir el desglose
    histórico exacto aunque el CSV cambie. `altura_preferida_cm` evita pedir
    la altura en cada rutina.
    """
    cur = conn.cursor()
    _agregar_columnas(
        cur,
        "predicciones_calorias",
        [
            ("altura_cm", "REAL"),
            ("modelo_snapshot", "TEXT"),
        ],
    )
    _agregar_columnas(
        cur,
        "usuarios",
        [
            ("altura_preferida_cm", "REAL"),
        ],
    )


# Versión, nombre y función aplicadora. El orden es obligatorio.
MIGRACIONES: List[Tuple[int, str, Callable[[sqlite3.Connection], None]]] = [
    (1, "esquema_inicial", _migracion_001_esquema_inicial),
    (2, "perfil_ampliado", _migracion_002_perfil_ampliado),
    (3, "tokens_y_metodo_calculo", _migracion_003_tokens_y_metodo),
    (4, "escuela_futbol", _migracion_004_escuela_futbol),
    (5, "usuarios_escuela", _migracion_005_usuarios_escuela),
    (6, "papelera_predicciones", _migracion_006_papelera_predicciones),
    (7, "google_signin", _migracion_007_google_signin),
    (8, "regresion_lineal", _migracion_008_regresion_lineal),
]


def _crear_tabla_migraciones(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            aplicada_en TEXT NOT NULL
        )
        """
    )


def aplicar_migraciones(conn: sqlite3.Connection) -> List[int]:
    """
    Aplica las migraciones pendientes y retorna las versiones ejecutadas.
    Es seguro llamarla en cada arranque: las ya aplicadas se omiten.
    """
    _crear_tabla_migraciones(conn)
    aplicadas = {
        int(fila["version"])
        for fila in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }

    ejecutadas: List[int] = []
    for version, nombre, funcion in MIGRACIONES:
        if version in aplicadas:
            continue
        funcion(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, nombre, aplicada_en) VALUES (?, ?, ?)",
            (version, nombre, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        ejecutadas.append(version)

    return ejecutadas


def listar_migraciones(path: Optional[str] = None) -> List[Dict[str, object]]:
    """Retorna el historial de migraciones aplicadas (para diagnóstico/tests)."""
    conn = get_connection(path)
    try:
        _crear_tabla_migraciones(conn)
        filas = conn.execute(
            "SELECT version, nombre, aplicada_en FROM schema_migrations ORDER BY version ASC"
        ).fetchall()
        return [dict(fila) for fila in filas]
    finally:
        conn.close()


def init_db(path: Optional[str] = None) -> None:
    """Inicializa o actualiza el esquema aplicando las migraciones versionadas."""
    conn = get_connection(path)
    try:
        aplicar_migraciones(conn)
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Respaldos (Willys_IA): copia consistente de la SQLite
# ----------------------------------------------------------------------


def crear_respaldo(destino: str) -> str:
    """
    Copia la base a `destino` con la API de backup de SQLite.

    A diferencia de copiar `app.db` a mano, esto se puede ejecutar con el
    servidor en marcha: SQLite escribe una foto consistente aunque haya
    asistencias o pagos entrando en ese momento.
    """
    origen = obtener_ruta_db()
    if not os.path.exists(origen):
        raise FileNotFoundError("Todavía no existe la base de datos.")

    carpeta = os.path.dirname(os.path.abspath(destino))
    os.makedirs(carpeta, exist_ok=True)

    con_origen = sqlite3.connect(origen)
    try:
        con_destino = sqlite3.connect(destino)
        try:
            con_origen.backup(con_destino)
        finally:
            con_destino.close()
    finally:
        con_origen.close()
    return destino


def respaldo_automatico(conservar: int = 10) -> Optional[str]:
    """
    Crea un respaldo por día en `data/respaldos/` al arrancar el servidor.

    - No hace nada si la base todavía no tiene cuentas (nada que perder).
    - Si ya existe el respaldo de hoy, no lo repite.
    - Conserva los últimos `conservar` respaldos automáticos.
    """
    origen = obtener_ruta_db()
    if not os.path.exists(origen):
        return None

    try:
        conn = get_connection(origen)
        try:
            cuentas = conn.execute("SELECT COUNT(*) FROM ef_usuarios").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    if not cuentas:
        return None

    carpeta = os.path.join(os.path.dirname(os.path.abspath(origen)), "respaldos")
    destino = os.path.join(
        carpeta, "escuela-" + datetime.now().strftime("%Y%m%d") + ".db"
    )
    if not os.path.exists(destino):
        crear_respaldo(destino)

    # Rotación: los nombres llevan AAAA-MM-DD, así que el orden alfabético
    # equivale al orden cronológico.
    try:
        archivos = sorted(
            nombre
            for nombre in os.listdir(carpeta)
            if nombre.startswith("escuela-") and nombre.endswith(".db")
        )
    except OSError:
        return destino

    for nombre in archivos[: -max(1, conservar)]:
        try:
            os.remove(os.path.join(carpeta, nombre))
        except OSError:
            pass
    return destino
