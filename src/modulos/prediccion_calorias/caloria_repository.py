# -*- coding: utf-8 -*-
"""
Capa de Persistencia de Predicciones de Calorías (Repository Layer).
Willys_IA: Almacenamiento en SQLite de predicciones por usuario.
"""

from datetime import datetime
from typing import List, Optional
from modulos.prediccion_calorias.caloria_model import Willys_IA_CaloriaModel
from database import get_connection


def _val(row, key: str, default=None):
    """Acceso defensivo a columnas (compatibilidad con DB antiguas migradas)."""
    try:
        return row[key]
    except (IndexError, KeyError):
        return default


class Willys_IA_CaloriaRepository:
    """Willys_IA: Repositorio SQLite para predicciones de calorías."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def _conn(self):
        return get_connection(self.db_path)

    def _row_to_model(self, row) -> Willys_IA_CaloriaModel:
        return Willys_IA_CaloriaModel(
            id=int(row["id"]),
            usuario_id=int(row["usuario_id"]),
            tipo_actividad=row["tipo_actividad"],
            peso_kg=float(row["peso_kg"]),
            duracion_min=float(row["duracion_min"]),
            met=float(row["met"]),
            fc_promedio=_val(row, "fc_promedio"),
            edad=_val(row, "edad"),
            sexo=_val(row, "sexo"),
            altura_cm=_val(row, "altura_cm"),
            modelo_snapshot=_val(row, "modelo_snapshot"),
            metodo_calculo=_val(row, "metodo_calculo", "MET") or "MET",
            calorias_estimadas=float(row["calorias_estimadas"]),
            fecha_registro=row["fecha_registro"],
            eliminado=bool(_val(row, "eliminado", 0)),
            fecha_eliminacion=_val(row, "fecha_eliminacion"),
        )

    def guardar(self, item: Willys_IA_CaloriaModel) -> Willys_IA_CaloriaModel:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO predicciones_calorias
                (usuario_id, tipo_actividad, peso_kg, duracion_min, met,
                 fc_promedio, edad, sexo, altura_cm, modelo_snapshot,
                 metodo_calculo, calorias_estimadas, fecha_registro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.usuario_id,
                    item.tipo_actividad,
                    item.peso_kg,
                    item.duracion_min,
                    item.met,
                    item.fc_promedio,
                    item.edad,
                    item.sexo,
                    item.altura_cm,
                    item.modelo_snapshot,
                    item.metodo_calculo,
                    item.calorias_estimadas,
                    item.fecha_registro,
                ),
            )
            conn.commit()
            item.id = int(cur.lastrowid)
            return item
        finally:
            conn.close()

    def obtener_por_id(
        self, usuario_id: int, registro_id: int, incluir_eliminados: bool = False
    ) -> Optional[Willys_IA_CaloriaModel]:
        """Retorna un registro propio; por omite excluye los que están en papelera."""
        condicion = "" if incluir_eliminados else " AND COALESCE(eliminado, 0) = 0"
        conn = self._conn()
        try:
            fila = conn.execute(
                "SELECT * FROM predicciones_calorias WHERE id = ? AND usuario_id = ?"
                + condicion,
                (int(registro_id), int(usuario_id)),
            ).fetchone()
            return self._row_to_model(fila) if fila is not None else None
        finally:
            conn.close()

    def eliminar(self, usuario_id: int, registro_id: int) -> bool:
        """Mueve un registro propio a la papelera (eliminación suave)."""
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                UPDATE predicciones_calorias
                SET eliminado = 1, fecha_eliminacion = ?
                WHERE id = ? AND usuario_id = ? AND COALESCE(eliminado, 0) = 0
                """,
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    int(registro_id),
                    int(usuario_id),
                ),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def restaurar(self, usuario_id: int, registro_id: int) -> bool:
        """Devuelve un registro de la papelera al historial activo."""
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                UPDATE predicciones_calorias
                SET eliminado = 0, fecha_eliminacion = NULL
                WHERE id = ? AND usuario_id = ? AND COALESCE(eliminado, 0) = 1
                """,
                (int(registro_id), int(usuario_id)),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def eliminar_definitivamente(self, usuario_id: int, registro_id: int) -> bool:
        """Borra de SQLite solo un registro que ya está en la papelera del usuario."""
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                DELETE FROM predicciones_calorias
                WHERE id = ? AND usuario_id = ? AND COALESCE(eliminado, 0) = 1
                """,
                (int(registro_id), int(usuario_id)),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def vaciar_papelera(self, usuario_id: int) -> int:
        """Elimina definitivamente todos los registros en papelera del usuario."""
        conn = self._conn()
        try:
            cur = conn.execute(
                """
                DELETE FROM predicciones_calorias
                WHERE usuario_id = ? AND COALESCE(eliminado, 0) = 1
                """,
                (int(usuario_id),),
            )
            conn.commit()
            return int(cur.rowcount)
        finally:
            conn.close()

    @staticmethod
    def _construir_filtros(
        usuario_id: int,
        q: Optional[str] = None,
        actividad: Optional[str] = None,
        solo_activos: bool = True,
    ) -> tuple:
        """Construye WHERE parametrizado (historial activo o papelera)."""
        estado = 0 if solo_activos else 1
        condiciones = ["usuario_id = ?", "COALESCE(eliminado, 0) = ?"]
        params: List[object] = [usuario_id, estado]
        if q and q.strip():
            condiciones.append("LOWER(tipo_actividad) LIKE ?")
            params.append(f"%{q.strip().lower()}%")
        if actividad and actividad.strip():
            condiciones.append("LOWER(tipo_actividad) LIKE ?")
            params.append(f"%{actividad.strip().lower()}%")
        return " AND ".join(condiciones), params

    def listar_por_usuario(self, usuario_id: int) -> List[Willys_IA_CaloriaModel]:
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT * FROM predicciones_calorias
                WHERE usuario_id = ? AND COALESCE(eliminado, 0) = 0
                ORDER BY id ASC
                """,
                (usuario_id,),
            ).fetchall()
            return [self._row_to_model(r) for r in rows]
        finally:
            conn.close()

    def listar_por_usuario_paginado(
        self,
        usuario_id: int,
        q: Optional[str] = None,
        actividad: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Willys_IA_CaloriaModel]:
        """Retorna una página del historial, del registro más reciente al más antiguo."""
        where, params = self._construir_filtros(usuario_id, q, actividad)
        conn = self._conn()
        try:
            rows = conn.execute(
                f"""
                SELECT * FROM predicciones_calorias
                WHERE {where}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (*params, int(limit), int(offset)),
            ).fetchall()
            return [self._row_to_model(r) for r in rows]
        finally:
            conn.close()

    def contar_por_usuario(
        self,
        usuario_id: int,
        q: Optional[str] = None,
        actividad: Optional[str] = None,
        solo_activos: bool = True,
    ) -> int:
        """Cantidad total de registros del usuario que cumplen los filtros."""
        where, params = self._construir_filtros(usuario_id, q, actividad, solo_activos)
        conn = self._conn()
        try:
            fila = conn.execute(
                f"SELECT COUNT(*) AS total FROM predicciones_calorias WHERE {where}",
                params,
            ).fetchone()
            return int(fila["total"] or 0)
        finally:
            conn.close()

    def sumar_calorias_por_usuario(
        self,
        usuario_id: int,
        q: Optional[str] = None,
        actividad: Optional[str] = None,
        solo_activos: bool = True,
    ) -> float:
        """Suma de calorías de todos los registros filtrados (no solo la página)."""
        where, params = self._construir_filtros(usuario_id, q, actividad, solo_activos)
        conn = self._conn()
        try:
            fila = conn.execute(
                f"SELECT COALESCE(SUM(calorias_estimadas), 0) AS total FROM predicciones_calorias WHERE {where}",
                params,
            ).fetchone()
            return round(float(fila["total"] or 0), 2)
        finally:
            conn.close()

    def listar_papelera_paginado(
        self,
        usuario_id: int,
        q: Optional[str] = None,
        actividad: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Willys_IA_CaloriaModel]:
        """Página de la papelera del usuario, más reciente primero."""
        where, params = self._construir_filtros(
            usuario_id, q, actividad, solo_activos=False
        )
        conn = self._conn()
        try:
            rows = conn.execute(
                f"""
                SELECT * FROM predicciones_calorias
                WHERE {where}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (*params, int(limit), int(offset)),
            ).fetchall()
            return [self._row_to_model(r) for r in rows]
        finally:
            conn.close()
