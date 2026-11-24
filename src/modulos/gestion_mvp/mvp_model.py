# -*- coding: utf-8 -*-
"""
Capa de Modelo y Entidades del Dominio (Model Layer).
Willys_IA: Define la estructura del dato y sus validaciones intrínsecas de integridad.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Willys_IA_ItemModel:
    """
    Willys_IA: Entidad de dominio central del Producto Mínimo Viable.
    Representa un elemento del negocio (donación, tarea de equipo, solicitud de ayuda o recurso).
    
    Campos de la entidad:
    - id: Entero autoincremental único (PK).
    - nombre: Texto descriptivo (mínimo 3 caracteres).
    - categoria_rubro: Categoría a la que pertenece.
    - estado: Estado del ciclo de vida ('ACTIVO', 'PENDIENTE', 'ENTREGADO', 'COMPLETADO').
    - valor_numerico: Cantidad física, monto o métrica (>= 0.0).
    - fecha_creacion: Marca temporal en formato legible.
    """
    id: int
    nombre: str
    categoria_rubro: str = "General"
    estado: str = "ACTIVO"
    valor_numerico: float = 0.0
    fecha_creacion: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    def validar(self) -> bool:
        """
        Willys_IA: Ejecuta las validaciones declaradas en docs/SPEC.md y docs/DATABASE.md.
        Retorna True si la entidad es válida; False si viola alguna regla del negocio.
        """
        # Validación RN-01: Nombre no vacío ni solo espacios (mínimo 3 caracteres)
        if not self.nombre or len(self.nombre.strip()) < 3:
            return False

        # Validación RN-02: Valor numérico no negativo
        if self.valor_numerico < 0:
            return False

        # Validación de estados válidos permitidos
        estados_validos = {"ACTIVO", "PENDIENTE", "EN_PROCESO", "ENTREGADO", "COMPLETADO", "CANCELADO"}
        if self.estado.upper() not in estados_validos:
            return False

        return True

    def to_dict(self) -> dict:
        """Willys_IA: Convierte la entidad a un diccionario serializable para JSON/Flask."""
        from dataclasses import asdict
        return asdict(self)

