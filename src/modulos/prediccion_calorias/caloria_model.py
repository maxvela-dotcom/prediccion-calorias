# -*- coding: utf-8 -*-
"""
Capa de Modelo del Dominio de Predicción de Calorías (Model Layer).
Willys_IA: Entidad y validaciones para una rutina y su predicción estimada.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Willys_IA_CaloriaModel:
    """
    Willys_IA: Representa una predicción de calorías quemadas para una rutina.

    Campos:
    - id: Identificador único (PK).
    - usuario_id: ID del usuario propietario.
    - tipo_actividad: Texto descriptivo de la actividad.
    - peso_kg: Peso del usuario en kilogramos (> 0).
    - duracion_min: Duración de la rutina en minutos (> 0).
    - met: Equivalente metabólico de la actividad (> 0).
    - fc_promedio: Frecuencia cardíaca promedio durante la rutina (opcional).
    - edad: Edad usada en el cálculo (opcional).
    - sexo: 'M', 'F' u 'OTRO' usado en el cálculo (opcional).
    - altura_cm: Altura usada como X2 en la regresión (opcional en registros antiguos).
    - modelo_snapshot: JSON con los β usados al predecir, para desgloses históricos exactos.
    - metodo_calculo: 'MET', 'KEYTEL' o 'REGRESION' (ecuación aplicada).
    - calorias_estimadas: Resultado calculado en kcal (>= 0).
    - fecha_registro: Marca temporal.
    - eliminado: 1 si está en la papelera (fuera del historial activo).
    - fecha_eliminacion: Marca temporal del movimiento a papelera (None si está activo).
    """
    id: int
    usuario_id: int
    tipo_actividad: str
    peso_kg: float
    duracion_min: float
    met: float
    fc_promedio: Optional[float] = None
    edad: Optional[int] = None
    sexo: Optional[str] = None
    altura_cm: Optional[float] = None
    modelo_snapshot: Optional[str] = None
    metodo_calculo: str = "MET"
    calorias_estimadas: float = 0.0
    fecha_registro: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    eliminado: bool = False
    fecha_eliminacion: Optional[str] = None

    def validar(self) -> bool:
        """Valida reglas del dominio para la predicción."""
        if self.usuario_id <= 0:
            return False
        if not self.tipo_actividad or len(self.tipo_actividad.strip()) < 3:
            return False
        if self.peso_kg <= 0 or self.duracion_min <= 0 or self.met <= 0:
            return False
        if self.calorias_estimadas < 0:
            return False

        if self.metodo_calculo not in {"MET", "KEYTEL", "REGRESION"}:
            return False

        if self.altura_cm is not None and not (100 <= float(self.altura_cm) <= 250):
            return False
        if self.metodo_calculo == "REGRESION" and self.altura_cm is None:
            return False

        if self.fc_promedio is not None and not (30 <= float(self.fc_promedio) <= 220):
            return False
        if self.edad is not None and not (10 <= int(self.edad) <= 120):
            return False
        if self.sexo is not None and str(self.sexo).upper() not in {"M", "F", "OTRO"}:
            return False

        return True

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)
