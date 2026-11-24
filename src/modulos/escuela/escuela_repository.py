# -*- coding: utf-8 -*-
"""
Capa de Persistencia (Repository Layer) — Módulo Escuela de Fútbol.
Willys_IA: Patrón Repositorio sobre SQLite. No contiene reglas de negocio,
solo operaciones de almacenamiento y consulta.
"""

from datetime import datetime
from typing import List, Optional

from database import get_connection
from modulos.escuela.escuela_model import (
    Willys_IA_Aviso,
    Willys_IA_Categoria,
    Willys_IA_Estudiante,
    Willys_IA_Sede,
    Willys_IA_Sesion,
)


class Willys_IA_EscuelaRepository:
    """Willys_IA: Repositorio de sedes, estudiantes, sesiones, asistencias y pagos."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def _conn(self):
        return get_connection(self.db_path)

    @staticmethod
    def _ahora() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    # Sedes y categorías
    # ------------------------------------------------------------------

    def listar_sedes(self) -> List[Willys_IA_Sede]:
        conn = self._conn()
        try:
            filas = conn.execute("SELECT id, nombre FROM ef_sedes ORDER BY nombre").fetchall()
            return [Willys_IA_Sede(id=int(f["id"]), nombre=f["nombre"]) for f in filas]
        finally:
            conn.close()

    def crear_sede(self, nombre: str) -> Willys_IA_Sede:
        conn = self._conn()
        try:
            cur = conn.execute("INSERT INTO ef_sedes (nombre) VALUES (?)", (nombre.strip(),))
            conn.commit()
            return Willys_IA_Sede(id=int(cur.lastrowid), nombre=nombre.strip())
        finally:
            conn.close()

    def listar_categorias(self) -> List[Willys_IA_Categoria]:
        conn = self._conn()
        try:
            filas = conn.execute(
                "SELECT id, nombre, precio_mensual FROM ef_categorias ORDER BY id"
            ).fetchall()
            return [
                Willys_IA_Categoria(
                    id=int(f["id"]),
                    nombre=f["nombre"],
                    precio_mensual=float(f["precio_mensual"]),
                )
                for f in filas
            ]
        finally:
            conn.close()

    def crear_categoria(self, nombre: str, precio_mensual: float) -> Willys_IA_Categoria:
        conn = self._conn()
        try:
            cur = conn.execute(
                "INSERT INTO ef_categorias (nombre, precio_mensual) VALUES (?, ?)",
                (nombre.strip(), float(precio_mensual)),
            )
            conn.commit()
            return Willys_IA_Categoria(
                id=int(cur.lastrowid),
                nombre=nombre.strip(),
                precio_mensual=float(precio_mensual),
            )
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Estudiantes
    # ------------------------------------------------------------------

    def _fila_a_estudiante(self, fila) -> Willys_IA_Estudiante:
        return Willys_IA_Estudiante(
            id=int(fila["id"]),
            nombre=fila["nombre"],
            categoria_id=int(fila["categoria_id"]),
            sede_id=int(fila["sede_id"]),
            qr_token=fila["qr_token"],
            becado=bool(fila["becado"]),
            estado=fila["estado"],
            fecha_registro=fila["fecha_registro"],
            categoria_nombre=fila["categoria_nombre"],
            sede_nombre=fila["sede_nombre"],
            precio_mensual=float(fila["precio_mensual"]),
        )

    _SELECT_ESTUDIANTE = """
        SELECT e.id, e.nombre, e.categoria_id, e.sede_id, e.qr_token, e.becado,
               e.estado, e.fecha_registro,
               c.nombre AS categoria_nombre, c.precio_mensual,
               s.nombre AS sede_nombre
        FROM ef_estudiantes e
        JOIN ef_categorias c ON c.id = e.categoria_id
        JOIN ef_sedes s ON s.id = e.sede_id
    """

    def listar_estudiantes(
        self,
        sede_id: Optional[int] = None,
        categoria_id: Optional[int] = None,
        solo_activos: bool = True,
    ) -> List[Willys_IA_Estudiante]:
        condiciones = []
        parametros: list = []
        if sede_id is not None:
            condiciones.append("e.sede_id = ?")
            parametros.append(int(sede_id))
        if categoria_id is not None:
            condiciones.append("e.categoria_id = ?")
            parametros.append(int(categoria_id))
        if solo_activos:
            condiciones.append("e.estado = 'ACTIVO'")

        consulta = self._SELECT_ESTUDIANTE
        if condiciones:
            consulta += " WHERE " + " AND ".join(condiciones)
        consulta += " ORDER BY s.nombre, c.nombre, e.nombre"

        conn = self._conn()
        try:
            filas = conn.execute(consulta, parametros).fetchall()
            return [self._fila_a_estudiante(f) for f in filas]
        finally:
            conn.close()

    def obtener_estudiante(self, estudiante_id: int) -> Optional[Willys_IA_Estudiante]:
        conn = self._conn()
        try:
            fila = conn.execute(
                self._SELECT_ESTUDIANTE + " WHERE e.id = ?", (int(estudiante_id),)
            ).fetchone()
            return self._fila_a_estudiante(fila) if fila else None
        finally:
            conn.close()

    def obtener_estudiante_por_token(self, qr_token: str) -> Optional[Willys_IA_Estudiante]:
        conn = self._conn()
        try:
            fila = conn.execute(
                self._SELECT_ESTUDIANTE + " WHERE upper(e.qr_token) = ?",
                ((qr_token or "").strip().upper(),),
            ).fetchone()
            return self._fila_a_estudiante(fila) if fila else None
        finally:
            conn.close()

    def crear_estudiante(
        self,
        nombre: str,
        categoria_id: int,
        sede_id: int,
        qr_token: str,
        becado: bool = False,
    ) -> Willys_IA_Estudiante:
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                INSERT INTO ef_estudiantes
                    (nombre, categoria_id, sede_id, qr_token, becado, estado, fecha_registro)
                VALUES (?, ?, ?, ?, ?, 'ACTIVO', ?)
                """,
                (
                    nombre.strip(),
                    int(categoria_id),
                    int(sede_id),
                    qr_token.strip().upper(),
                    1 if becado else 0,
                    self._ahora(),
                ),
            )
            conn.commit()
            estudiante = self.obtener_estudiante(int(cur.lastrowid))
            assert estudiante is not None
            return estudiante
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Sesiones
    # ------------------------------------------------------------------

    def _fila_a_sesion(self, fila) -> Willys_IA_Sesion:
        return Willys_IA_Sesion(
            id=int(fila["id"]),
            sede_id=int(fila["sede_id"]),
            categoria_id=int(fila["categoria_id"]),
            fecha=fila["fecha"],
            hora=fila["hora"],
            entrenador=fila["entrenador"],
            creada_en=fila["creada_en"],
            sede_nombre=fila["sede_nombre"],
            categoria_nombre=fila["categoria_nombre"],
        )

    _SELECT_SESION = """
        SELECT s.id, s.sede_id, s.categoria_id, s.fecha, s.hora, s.entrenador,
               s.creada_en, se.nombre AS sede_nombre, c.nombre AS categoria_nombre
        FROM ef_sesiones s
        JOIN ef_sedes se ON se.id = s.sede_id
        JOIN ef_categorias c ON c.id = s.categoria_id
    """

    def buscar_sesion(
        self, sede_id: int, categoria_id: int, fecha: str, hora: str
    ) -> Optional[Willys_IA_Sesion]:
        conn = self._conn()
        try:
            fila = conn.execute(
                self._SELECT_SESION
                + " WHERE s.sede_id = ? AND s.categoria_id = ? AND s.fecha = ? AND s.hora = ?",
                (int(sede_id), int(categoria_id), fecha, hora),
            ).fetchone()
            return self._fila_a_sesion(fila) if fila else None
        finally:
            conn.close()

    def crear_sesion(
        self, sede_id: int, categoria_id: int, fecha: str, hora: str, entrenador: str
    ) -> Willys_IA_Sesion:
        existente = self.buscar_sesion(sede_id, categoria_id, fecha, hora)
        if existente:
            return existente
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                INSERT INTO ef_sesiones
                    (sede_id, categoria_id, fecha, hora, entrenador, creada_en)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (int(sede_id), int(categoria_id), fecha, hora, entrenador.strip(), self._ahora()),
            )
            conn.commit()
            sesion = self.obtener_sesion(int(cur.lastrowid))
            assert sesion is not None
            return sesion
        finally:
            conn.close()

    def obtener_sesion(self, sesion_id: int) -> Optional[Willys_IA_Sesion]:
        conn = self._conn()
        try:
            fila = conn.execute(
                self._SELECT_SESION + " WHERE s.id = ?", (int(sesion_id),)
            ).fetchone()
            return self._fila_a_sesion(fila) if fila else None
        finally:
            conn.close()

    def listar_sesiones(self, fecha: Optional[str] = None, limite: int = 30) -> List[Willys_IA_Sesion]:
        conn = self._conn()
        try:
            consulta = self._SELECT_SESION
            parametros: list = []
            if fecha:
                consulta += " WHERE s.fecha = ?"
                parametros.append(fecha)
            consulta += " ORDER BY s.fecha DESC, s.hora DESC, se.nombre LIMIT ?"
            parametros.append(int(limite))
            filas = conn.execute(consulta, parametros).fetchall()
            return [self._fila_a_sesion(f) for f in filas]
        finally:
            conn.close()

    def contar_sesiones_hoy(self, hoy: str) -> int:
        conn = self._conn()
        try:
            fila = conn.execute(
                "SELECT COUNT(*) AS total FROM ef_sesiones WHERE fecha = ?", (hoy,)
            ).fetchone()
            return int(fila["total"])
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Asistencias
    # ------------------------------------------------------------------

    def registrar_asistencia(
        self, sesion_id: int, estudiante_id: int, metodo: str
    ) -> int:
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                INSERT INTO ef_asistencias
                    (sesion_id, estudiante_id, metodo, registrada_en)
                VALUES (?, ?, ?, ?)
                """,
                (int(sesion_id), int(estudiante_id), metodo, self._ahora()),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def obtener_asistencia(self, sesion_id: int, estudiante_id: int):
        conn = self._conn()
        try:
            return conn.execute(
                "SELECT id FROM ef_asistencias WHERE sesion_id = ? AND estudiante_id = ?",
                (int(sesion_id), int(estudiante_id)),
            ).fetchone()
        finally:
            conn.close()

    def listar_asistencias(self, sesion_id: int):
        conn = self._conn()
        try:
            filas = conn.execute(
                """
                SELECT a.id, a.sesion_id, a.estudiante_id, a.metodo, a.registrada_en,
                       e.nombre AS estudiante_nombre
                FROM ef_asistencias a
                JOIN ef_estudiantes e ON e.id = a.estudiante_id
                WHERE a.sesion_id = ?
                ORDER BY a.registrada_en ASC, e.nombre ASC
                """,
                (int(sesion_id),),
            ).fetchall()
            return [dict(f) for f in filas]
        finally:
            conn.close()

    def listar_ausentes(self, sesion_id: int) -> List[Willys_IA_Estudiante]:
        conn = self._conn()
        try:
            filas = conn.execute(
                self._SELECT_ESTUDIANTE
                + """
                JOIN ef_sesiones ses
                  ON ses.sede_id = e.sede_id AND ses.categoria_id = e.categoria_id
                WHERE ses.id = ? AND e.estado = 'ACTIVO'
                  AND NOT EXISTS (
                      SELECT 1 FROM ef_asistencias a
                      WHERE a.sesion_id = ses.id AND a.estudiante_id = e.id
                  )
                ORDER BY e.nombre
                """,
                (int(sesion_id),),
            ).fetchall()
            return [self._fila_a_estudiante(f) for f in filas]
        finally:
            conn.close()

    def contar_asistencias_hoy(self, hoy: str) -> int:
        conn = self._conn()
        try:
            fila = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM ef_asistencias a
                JOIN ef_sesiones s ON s.id = a.sesion_id
                WHERE s.fecha = ?
                """,
                (hoy,),
            ).fetchone()
            return int(fila["total"])
        finally:
            conn.close()

    def contar_ausentes_hoy(self, hoy: str) -> int:
        conn = self._conn()
        try:
            fila = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM ef_sesiones s
                JOIN ef_estudiantes e
                  ON e.sede_id = s.sede_id
                 AND e.categoria_id = s.categoria_id
                 AND e.estado = 'ACTIVO'
                WHERE s.fecha = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM ef_asistencias a
                      WHERE a.sesion_id = s.id AND a.estudiante_id = e.id
                  )
                """,
                (hoy,),
            ).fetchone()
            return int(fila["total"])
        finally:
            conn.close()

    def contar_asistencias_periodo(self, estudiante_id: int, periodo: str) -> int:
        conn = self._conn()
        try:
            fila = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM ef_asistencias a
                JOIN ef_sesiones s ON s.id = a.sesion_id
                WHERE a.estudiante_id = ? AND substr(s.fecha, 1, 7) = ?
                """,
                (int(estudiante_id), periodo),
            ).fetchone()
            return int(fila["total"])
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Avisos
    # ------------------------------------------------------------------

    def crear_aviso(self, sesion_id: int, estudiante_id: int) -> bool:
        """Inserta un aviso pendiente. Devuelve False si ya existía (idempotente)."""
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO ef_avisos
                    (sesion_id, estudiante_id, estado, creada_en)
                VALUES (?, ?, 'PENDIENTE', ?)
                """,
                (int(sesion_id), int(estudiante_id), self._ahora()),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def listar_avisos(
        self, estado: Optional[str] = None, sesion_id: Optional[int] = None
    ) -> List[Willys_IA_Aviso]:
        condiciones = []
        parametros: list = []
        if estado:
            condiciones.append("av.estado = ?")
            parametros.append(estado.upper())
        if sesion_id is not None:
            condiciones.append("av.sesion_id = ?")
            parametros.append(int(sesion_id))

        consulta = """
            SELECT av.id, av.sesion_id, av.estudiante_id, av.estado,
                   av.creada_en, av.enviada_en, e.nombre AS estudiante_nombre,
                   s.fecha, s.hora, c.nombre AS categoria_nombre,
                   se.nombre AS sede_nombre
            FROM ef_avisos av
            JOIN ef_estudiantes e ON e.id = av.estudiante_id
            JOIN ef_sesiones s ON s.id = av.sesion_id
            JOIN ef_categorias c ON c.id = s.categoria_id
            JOIN ef_sedes se ON se.id = s.sede_id
        """
        if condiciones:
            consulta += " WHERE " + " AND ".join(condiciones)
        consulta += " ORDER BY av.estado ASC, s.fecha DESC, av.id DESC"

        conn = self._conn()
        try:
            filas = conn.execute(consulta, parametros).fetchall()
            return [
                Willys_IA_Aviso(
                    id=int(f["id"]),
                    sesion_id=int(f["sesion_id"]),
                    estudiante_id=int(f["estudiante_id"]),
                    estado=f["estado"],
                    creada_en=f["creada_en"],
                    enviada_en=f["enviada_en"] or "",
                    estudiante_nombre=f["estudiante_nombre"],
                    fecha=f["fecha"],
                    hora=f["hora"],
                    categoria_nombre=f["categoria_nombre"],
                    sede_nombre=f["sede_nombre"],
                )
                for f in filas
            ]
        finally:
            conn.close()

    def obtener_aviso(self, aviso_id: int) -> Optional[Willys_IA_Aviso]:
        avisos = [a for a in self.listar_avisos() if a.id == int(aviso_id)]
        return avisos[0] if avisos else None

    def marcar_aviso_enviado(self, aviso_id: int) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                UPDATE ef_avisos
                SET estado = 'ENVIADA', enviada_en = ?
                WHERE id = ? AND estado = 'PENDIENTE'
                """,
                (self._ahora(), int(aviso_id)),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def contar_avisos_pendientes(self) -> int:
        conn = self._conn()
        try:
            fila = conn.execute(
                "SELECT COUNT(*) AS total FROM ef_avisos WHERE estado = 'PENDIENTE'"
            ).fetchone()
            return int(fila["total"])
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Pagos
    # ------------------------------------------------------------------

    def obtener_pago(self, estudiante_id: int, periodo: str):
        conn = self._conn()
        try:
            return conn.execute(
                """
                SELECT estudiante_id, periodo, monto, estado, fecha_pago
                FROM ef_pagos
                WHERE estudiante_id = ? AND periodo = ?
                """,
                (int(estudiante_id), periodo),
            ).fetchone()
        finally:
            conn.close()

    def guardar_pago(
        self, estudiante_id: int, periodo: str, monto: float, estado: str, fecha_pago: str
    ) -> None:
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO ef_pagos
                    (estudiante_id, periodo, monto, estado, fecha_pago)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(estudiante_id, periodo) DO UPDATE SET
                    monto = excluded.monto,
                    estado = excluded.estado,
                    fecha_pago = excluded.fecha_pago
                """,
                (int(estudiante_id), periodo, float(monto), estado, fecha_pago),
            )
            conn.commit()
        finally:
            conn.close()

    def contar_estudiantes_activos(self) -> int:
        conn = self._conn()
        try:
            fila = conn.execute(
                "SELECT COUNT(*) AS total FROM ef_estudiantes WHERE estado = 'ACTIVO'"
            ).fetchone()
            return int(fila["total"])
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Willys_IA: usuarios de la app compartida (login por rol)
    # ------------------------------------------------------------------

    def listar_usuarios_escuela(self) -> List[dict]:
        conn = self._conn()
        try:
            filas = conn.execute(
                """
                SELECT id, usuario, nombre, rol, estudiante_id, activo
                FROM ef_usuarios ORDER BY id
                """
            ).fetchall()
            return [dict(f) for f in filas]
        finally:
            conn.close()

    def obtener_usuario_por_nombre(self, usuario: str) -> Optional[dict]:
        conn = self._conn()
        try:
            fila = conn.execute(
                """
                SELECT id, usuario, nombre, password_hash, rol, estudiante_id, activo
                FROM ef_usuarios WHERE usuario = ?
                """,
                ((usuario or "").strip().lower(),),
            ).fetchone()
            return dict(fila) if fila else None
        finally:
            conn.close()

    def crear_usuario_escuela(
        self,
        usuario: str,
        nombre: str,
        password_hash: str,
        rol: str,
        estudiante_id: Optional[int] = None,
    ) -> bool:
        """Crea un usuario si no existe. Devuelve True si lo creó."""
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO ef_usuarios
                    (usuario, nombre, password_hash, rol, estudiante_id, activo, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    usuario.strip().lower(),
                    nombre.strip(),
                    password_hash,
                    rol,
                    None if estudiante_id is None else int(estudiante_id),
                    self._ahora(),
                ),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def asignar_estudiante_usuario(self, usuario: str, estudiante_id: int) -> None:
        conn = self._conn()
        try:
            conn.execute(
                """
                UPDATE ef_usuarios SET estudiante_id = ?
                WHERE usuario = ? AND estudiante_id IS NULL
                """,
                (int(estudiante_id), usuario.strip().lower()),
            )
            conn.commit()
        finally:
            conn.close()

    def contar_usuarios_escuela(self) -> int:
        conn = self._conn()
        try:
            fila = conn.execute("SELECT COUNT(*) AS total FROM ef_usuarios").fetchone()
            return int(fila["total"])
        finally:
            conn.close()

    def listar_usuarios_detalle(self) -> List[dict]:
        """Cuentas con el nombre del alumno asociado (si es rol ALUMNO)."""
        conn = self._conn()
        try:
            filas = conn.execute(
                """
                SELECT u.id, u.usuario, u.nombre, u.rol, u.estudiante_id, u.activo,
                       e.nombre AS estudiante
                FROM ef_usuarios u
                LEFT JOIN ef_estudiantes e ON e.id = u.estudiante_id
                ORDER BY u.rol, u.usuario
                """
            ).fetchall()
            return [dict(f) for f in filas]
        finally:
            conn.close()

    def cambiar_password_usuario(self, usuario: str, password_hash: str) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute(
                "UPDATE ef_usuarios SET password_hash = ? WHERE usuario = ?",
                (password_hash, (usuario or "").strip().lower()),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def eliminar_estudiante(self, estudiante_id: int) -> bool:
        """
        Baja lógica: el alumno pasa a INACTIVO y conserva su historial.
        No se borra la fila para no romper asistencias, avisos ni pagos.
        """
        conn = self._conn()
        try:
            cur = conn.execute(
                "UPDATE ef_estudiantes SET estado = 'INACTIVO' WHERE id = ?",
                (int(estudiante_id),),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Vista del alumno: historial de asistencias y faltas del periodo
    # ------------------------------------------------------------------

    def listar_historial_estudiante(
        self, estudiante_id: int, periodo: str
    ) -> List[dict]:
        """
        Una fila por sesión del grupo del alumno en el periodo, con o sin asistencia.
        Así el alumno ve también sus faltas sin exponer los datos de los demás.
        """
        conn = self._conn()
        try:
            filas = conn.execute(
                """
                SELECT s.fecha, s.hora, s.entrenador,
                       se.nombre AS sede, c.nombre AS categoria,
                       a.metodo, a.registrada_en,
                       CASE WHEN a.id IS NULL THEN 0 ELSE 1 END AS asistio
                FROM ef_sesiones s
                JOIN ef_estudiantes e
                  ON e.sede_id = s.sede_id AND e.categoria_id = s.categoria_id
                JOIN ef_sedes se ON se.id = s.sede_id
                JOIN ef_categorias c ON c.id = s.categoria_id
                LEFT JOIN ef_asistencias a
                  ON a.sesion_id = s.id AND a.estudiante_id = e.id
                WHERE e.id = ? AND substr(s.fecha, 1, 7) = ?
                ORDER BY s.fecha DESC, s.hora DESC
                """,
                (int(estudiante_id), periodo),
            ).fetchall()
            return [dict(f) for f in filas]
        finally:
            conn.close()
