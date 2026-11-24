# -*- coding: utf-8 -*-
"""
Capa de Persistencia de Usuarios (Repository Layer).
Willys_IA: Patrón Repositorio para la entidad Usuario (SQLite).
"""

from typing import List, Optional
from modulos.usuarios.usuario_model import Willys_IA_UsuarioModel
from database import get_connection


def _val(row, key: str, default=None):
    """Acceso defensivo a columnas (compatibilidad con DB antiguas migradas)."""
    try:
        return row[key]
    except (IndexError, KeyError):
        return default


class Willys_IA_UsuarioRepository:
    """
    Willys_IA: Repositorio responsable de almacenar y consultar usuarios en SQLite.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def _conn(self):
        return get_connection(self.db_path)

    def _row_to_model(self, row) -> Willys_IA_UsuarioModel:
        return Willys_IA_UsuarioModel(
            id=int(row["id"]),
            nombre_completo=row["nombre_completo"],
            email=row["email"],
            password_hash=row["password_hash"],
            rol=row["rol"],
            estado=row["estado"],
            fecha_registro=row["fecha_registro"],
            peso_preferido_kg=_val(row, "peso_preferido_kg"),
            altura_preferida_cm=_val(row, "altura_preferida_cm"),
            edad=_val(row, "edad"),
            sexo=_val(row, "sexo"),
            fc_reposo=_val(row, "fc_reposo"),
            email_verificado=int(_val(row, "email_verificado", 0) or 0),
            token_verificacion=_val(row, "token_verificacion"),
            token_expira=_val(row, "token_expira"),
            reset_token=_val(row, "reset_token"),
            reset_expira=_val(row, "reset_expira"),
            proveedor=_val(row, "proveedor", "LOCAL") or "LOCAL",
            google_sub=_val(row, "google_sub"),
        )

    def guardar(self, usuario: Willys_IA_UsuarioModel) -> Willys_IA_UsuarioModel:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO usuarios
                (nombre_completo, email, password_hash, rol, estado, fecha_registro,
                 peso_preferido_kg, altura_preferida_cm, edad, sexo, fc_reposo,
                 email_verificado, proveedor, google_sub)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    usuario.nombre_completo,
                    usuario.email,
                    usuario.password_hash,
                    usuario.rol,
                    usuario.estado,
                    usuario.fecha_registro,
                    usuario.peso_preferido_kg,
                    usuario.altura_preferida_cm,
                    usuario.edad,
                    usuario.sexo,
                    usuario.fc_reposo,
                    int(usuario.email_verificado or 0),
                    str(usuario.proveedor or "LOCAL").upper(),
                    usuario.google_sub or None,
                ),
            )
            conn.commit()
            usuario.id = int(cur.lastrowid)
            return usuario
        finally:
            conn.close()

    def obtener_todos(self) -> List[Willys_IA_UsuarioModel]:
        conn = self._conn()
        try:
            rows = conn.execute("SELECT * FROM usuarios ORDER BY id ASC").fetchall()
            return [self._row_to_model(r) for r in rows]
        finally:
            conn.close()

    def obtener_por_id(self, id_usuario: int) -> Optional[Willys_IA_UsuarioModel]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (id_usuario,)).fetchone()
            return self._row_to_model(row) if row else None
        finally:
            conn.close()

    def obtener_por_email(self, email: str) -> Optional[Willys_IA_UsuarioModel]:
        email_normalizado = (email or "").strip().lower()
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM usuarios WHERE lower(email) = ?", (email_normalizado,)).fetchone()
            return self._row_to_model(row) if row else None
        finally:
            conn.close()

    def obtener_por_google_sub(self, google_sub: str) -> Optional[Willys_IA_UsuarioModel]:
        """Busca un usuario por el identificador único de su cuenta de Google."""
        sub = (google_sub or "").strip()
        if not sub:
            return None
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM usuarios WHERE google_sub = ? LIMIT 1", (sub,)
            ).fetchone()
            return self._row_to_model(row) if row else None
        finally:
            conn.close()

    def vincular_google(self, id_usuario: int, google_sub: str) -> bool:
        """
        Asocia una cuenta de Google a un usuario ya existente por correo verificado.

        No sobrescribe un vínculo distinto: si el usuario ya tiene otro
        `google_sub`, la actualización no afecta ninguna fila.
        """
        sub = (google_sub or "").strip()
        if not sub:
            return False
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                UPDATE usuarios
                SET proveedor = 'GOOGLE', google_sub = ?, email_verificado = 1,
                    token_verificacion = NULL, token_expira = NULL
                WHERE id = ? AND (google_sub IS NULL OR google_sub = ?)
                """,
                (sub, int(id_usuario), sub),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def cambiar_estado(self, id_usuario: int, nuevo_estado: str) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute(
                "UPDATE usuarios SET estado = ? WHERE id = ?",
                (nuevo_estado.strip().upper(), id_usuario),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def actualizar_perfil(self, id_usuario: int, campos: dict) -> Optional[Willys_IA_UsuarioModel]:
        """
        Actualiza solo los campos de perfil presentes en `campos`.
        Columnas permitidas: peso_preferido_kg, altura_preferida_cm, edad, sexo, fc_reposo.
        """
        permitidos = {
            "peso_preferido_kg", "altura_preferida_cm", "edad", "sexo", "fc_reposo"
        }
        asignaciones = {k: v for k, v in (campos or {}).items() if k in permitidos}
        if not asignaciones:
            return self.obtener_por_id(id_usuario)

        conn = self._conn()
        try:
            columnas = ", ".join(f"{c} = ?" for c in asignaciones)
            valores = list(asignaciones.values()) + [id_usuario]
            cur = conn.execute(f"UPDATE usuarios SET {columnas} WHERE id = ?", valores)
            conn.commit()
            if cur.rowcount == 0:
                return None
        finally:
            conn.close()
        return self.obtener_por_id(id_usuario)

    # ------------------------------------------------------------------
    # Verificación de correo (tokens de un solo uso, simulación local)
    # ------------------------------------------------------------------

    def guardar_token_verificacion(self, id_usuario: int, token: str, expira: str) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                UPDATE usuarios
                SET token_verificacion = ?, token_expira = ?, email_verificado = 0
                WHERE id = ?
                """,
                (token, expira, id_usuario),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def obtener_por_token_verificacion(self, token: str) -> Optional[Willys_IA_UsuarioModel]:
        if not token:
            return None
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM usuarios WHERE token_verificacion = ? LIMIT 1", (token,)
            ).fetchone()
            return self._row_to_model(row) if row else None
        finally:
            conn.close()

    def marcar_email_verificado(self, id_usuario: int) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                UPDATE usuarios
                SET email_verificado = 1, token_verificacion = NULL, token_expira = NULL
                WHERE id = ?
                """,
                (id_usuario,),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Recuperación de contraseña (tokens de un solo uso)
    # ------------------------------------------------------------------

    def guardar_token_reset(self, id_usuario: int, token: str, expira: str) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute(
                "UPDATE usuarios SET reset_token = ?, reset_expira = ? WHERE id = ?",
                (token, expira, id_usuario),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def obtener_por_token_reset(self, token: str) -> Optional[Willys_IA_UsuarioModel]:
        if not token:
            return None
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM usuarios WHERE reset_token = ? LIMIT 1", (token,)
            ).fetchone()
            return self._row_to_model(row) if row else None
        finally:
            conn.close()

    def actualizar_password(self, id_usuario: int, password_hash: str) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                UPDATE usuarios
                SET password_hash = ?, reset_token = NULL, reset_expira = NULL
                WHERE id = ?
                """,
                (password_hash, id_usuario),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
