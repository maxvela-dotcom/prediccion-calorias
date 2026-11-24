# -*- coding: utf-8 -*-
"""
Capa de Dominio (Model Layer) — Módulo Escuela de Fútbol.
Willys_IA: Entidades con tipado estricto (@dataclass) y validaciones intrínsecas.

Reglas del contrato (docs/SPEC_ESCUELA.md):
- RN-E01: un estudiante pertenece a una categoría y a una sede.
- RN-E02: cada estudiante tiene un token QR único e intransferible.
- RN-E03: una asistencia es única por sesión y estudiante.
- RN-E04: un aviso es único por sesión y estudiante.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Willys_IA_Sede:
    """Sede física donde entrena la escuela."""

    id: int
    nombre: str

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "nombre": self.nombre}


@dataclass
class Willys_IA_Categoria:
    """Categoría deportiva con su tarifa mensual de referencia."""

    id: int
    nombre: str
    precio_mensual: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "precio_mensual": round(float(self.precio_mensual), 2),
        }


@dataclass
class Willys_IA_Estudiante:
    """Alumno inscrito en la escuela."""

    id: int
    nombre: str
    categoria_id: int
    sede_id: int
    qr_token: str
    becado: bool = False
    estado: str = "ACTIVO"
    fecha_registro: str = ""
    categoria_nombre: str = ""
    sede_nombre: str = ""
    precio_mensual: float = 0.0

    def validar(self) -> bool:
        """Willys_IA: valida la integridad mínima de la entidad."""
        return (
            bool((self.nombre or "").strip())
            and len(self.nombre.strip()) >= 3
            and bool((self.qr_token or "").strip())
            and self.estado in ("ACTIVO", "INACTIVO")
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "categoria_id": self.categoria_id,
            "categoria": self.categoria_nombre,
            "sede_id": self.sede_id,
            "sede": self.sede_nombre,
            "qr_token": self.qr_token,
            "becado": bool(self.becado),
            "estado": self.estado,
            "precio_mensual": round(float(self.precio_mensual), 2),
        }


@dataclass
class Willys_IA_Sesion:
    """Entrenamiento programado para una sede y categoría."""

    id: int
    sede_id: int
    categoria_id: int
    fecha: str
    hora: str
    entrenador: str
    creada_en: str = ""
    sede_nombre: str = ""
    categoria_nombre: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sede_id": self.sede_id,
            "sede": self.sede_nombre,
            "categoria_id": self.categoria_id,
            "categoria": self.categoria_nombre,
            "fecha": self.fecha,
            "hora": self.hora,
            "entrenador": self.entrenador,
        }


@dataclass
class Willys_IA_Asistencia:
    """Registro de presencia de un estudiante en una sesión."""

    id: int
    sesion_id: int
    estudiante_id: int
    metodo: str
    registrada_en: str
    estudiante_nombre: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sesion_id": self.sesion_id,
            "estudiante_id": self.estudiante_id,
            "estudiante": self.estudiante_nombre,
            "metodo": self.metodo,
            "registrada_en": self.registrada_en,
        }


@dataclass
class Willys_IA_Aviso:
    """Aviso de ausencia que el administrador revisa y envía al padre."""

    id: int
    sesion_id: int
    estudiante_id: int
    estado: str
    creada_en: str
    enviada_en: str = ""
    estudiante_nombre: str = ""
    fecha: str = ""
    hora: str = ""
    categoria_nombre: str = ""
    sede_nombre: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sesion_id": self.sesion_id,
            "estudiante_id": self.estudiante_id,
            "estudiante": self.estudiante_nombre,
            "estado": self.estado,
            "creada_en": self.creada_en,
            "enviada_en": self.enviada_en,
            "fecha": self.fecha,
            "hora": self.hora,
            "categoria": self.categoria_nombre,
            "sede": self.sede_nombre,
        }


@dataclass
class Willys_IA_Cobro:
    """Resultado del cálculo mensual por estudiante (no es un pago todavía)."""

    estudiante_id: int
    nombre: str
    categoria: str
    sede: str
    asistencias: int
    monto: float
    motivo: str
    estado_pago: str
    fecha_pago: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "estudiante_id": self.estudiante_id,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "sede": self.sede,
            "asistencias": self.asistencias,
            "monto": round(float(self.monto), 2),
            "motivo": self.motivo,
            "estado_pago": self.estado_pago,
            "fecha_pago": self.fecha_pago,
        }
