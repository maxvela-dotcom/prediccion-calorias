# -*- coding: utf-8 -*-
"""
Capa de Persistencia y Acceso a Datos (Repository Layer).
Willys_IA: Patrón Repositorio (SQLite).
"""

from typing import List, Optional
from modulos.gestion_mvp.mvp_model import Willys_IA_ItemModel
from database import get_connection


class Willys_IA_ItemRepository:
    """
    Willys_IA: Repositorio responsable de guardar, buscar y actualizar entidades en SQLite.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def _conn(self):
        return get_connection(self.db_path)

    def _row_to_model(self, row) -> Willys_IA_ItemModel:
        return Willys_IA_ItemModel(
            id=int(row["id"]),
            nombre=row["nombre"],
            categoria_rubro=row["categoria_rubro"],
            estado=row["estado"],
            valor_numerico=float(row["valor_numerico"]),
            fecha_creacion=row["fecha_creacion"],
        )

    def guardar(self, item: Willys_IA_ItemModel) -> Willys_IA_ItemModel:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO elementos_mvp (nombre, categoria_rubro, estado, valor_numerico, fecha_creacion)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item.nombre, item.categoria_rubro, item.estado, item.valor_numerico, item.fecha_creacion),
            )
            conn.commit()
            item.id = int(cur.lastrowid)
            return item
        finally:
            conn.close()

    def obtener_todos(self) -> List[Willys_IA_ItemModel]:
        conn = self._conn()
        try:
            rows = conn.execute("SELECT * FROM elementos_mvp ORDER BY id ASC").fetchall()
            return [self._row_to_model(r) for r in rows]
        finally:
            conn.close()

    def obtener_por_id(self, id_item: int) -> Optional[Willys_IA_ItemModel]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM elementos_mvp WHERE id = ?", (id_item,)).fetchone()
            return self._row_to_model(row) if row else None
        finally:
            conn.close()

    def obtener_por_nombre_activo(self, nombre: str) -> Optional[Willys_IA_ItemModel]:
        nombre_normalizado = (nombre or "").strip().lower()
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM elementos_mvp WHERE lower(nombre) = ? AND estado = 'ACTIVO' LIMIT 1",
                (nombre_normalizado,),
            ).fetchone()
            return self._row_to_model(row) if row else None
        finally:
            conn.close()

    def actualizar_estado(self, id_item: int, nuevo_estado: str) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute(
                "UPDATE elementos_mvp SET estado = ? WHERE id = ?",
                (nuevo_estado.strip().upper(), id_item),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
