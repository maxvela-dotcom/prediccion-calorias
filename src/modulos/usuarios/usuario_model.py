# -*- coding: utf-8 -*-
"""
Capa de Modelo y Entidad de Usuario (Model Layer).
Willys_IA: Estructura de datos tipada para la gestión de usuarios del sistema.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Valores canónicos de sexo usados por la ecuación de Keytel.
SEXOS_VALIDOS = {"M", "F", "OTRO"}


@dataclass
class Willys_IA_UsuarioModel:
    """
    Willys_IA: Entidad que representa un usuario o actor del sistema.

    Campos de la entidad:
    - id: Entero autoincremental único (PK).
    - nombre_completo: Nombre y apellido del usuario (mínimo 3 caracteres).
    - email: Correo electrónico institucional o de contacto.
    - password_hash: Hash seguro de la contraseña (nunca texto plano).
    - rol: Rol en el sistema ('ESTUDIANTE', 'DOCENTE', 'VOLUNTARIO', 'ADMIN').
    - estado: 'ACTIVO' o 'INACTIVO'.
    - fecha_registro: Marca temporal de creación.
    - peso_preferido_kg: Preferencia de perfil (opcional, > 0 y <= 500).
    - altura_preferida_cm: Altura del perfil (opcional, 100 a 250 cm), usada como X2.
    - edad: Edad del usuario (opcional, 10 a 120 años).
    - sexo: 'M' (masculino), 'F' (femenino) u 'OTRO'.
    - fc_reposo: Frecuencia cardíaca en reposo en ppm (opcional, 30 a 220).
    - email_verificado: 1 si el correo fue verificado, 0 si está pendiente.
    - token_verificacion / token_expira: token de un solo uso para verificar correo.
    - reset_token / reset_expira: token de un solo uso para restablecer contraseña.
    - proveedor: 'LOCAL' (correo/contraseña) o 'GOOGLE' (Google Sign-In).
    - google_sub: identificador único de la cuenta de Google (solo si proveedor = GOOGLE).
    """
    id: int
    nombre_completo: str
    email: str
    password_hash: str = ""
    rol: str = "ESTUDIANTE"
    estado: str = "ACTIVO"
    fecha_registro: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    peso_preferido_kg: Optional[float] = None
    altura_preferida_cm: Optional[float] = None
    edad: Optional[int] = None
    sexo: Optional[str] = None
    fc_reposo: Optional[float] = None
    email_verificado: int = 0
    token_verificacion: Optional[str] = None
    token_expira: Optional[str] = None
    reset_token: Optional[str] = None
    reset_expira: Optional[str] = None
    proveedor: str = "LOCAL"
    google_sub: Optional[str] = None

    def validar(self) -> bool:
        """
        Willys_IA: Valida las reglas de integridad del usuario.
        - Nombre no vacío (mínimo 3 caracteres).
        - Email debe contener '@' y un punto.
        - Password hash presente (mínimo 8 caracteres para hash/valor seguro).
        - Rol debe pertenecer a los permitidos.
        - Peso, edad, sexo y FC de reposo (si existen) deben estar en rango.
        """
        nombre_limpio = (self.nombre_completo or "").strip()
        if len(nombre_limpio) < 3:
            return False

        email_limpio = (self.email or "").strip()
        if "@" not in email_limpio or "." not in email_limpio:
            return False

        if not self.password_hash or len(self.password_hash) < 8:
            return False

        roles_validos = {"ESTUDIANTE", "DOCENTE", "VOLUNTARIO", "ADMIN", "COORDINADOR"}
        if self.rol.upper() not in roles_validos:
            return False

        estados_validos = {"ACTIVO", "INACTIVO"}
        if self.estado.upper() not in estados_validos:
            return False

        proveedores_validos = {"LOCAL", "GOOGLE"}
        if str(self.proveedor).upper() not in proveedores_validos:
            return False
        if str(self.proveedor).upper() == "GOOGLE" and not (self.google_sub or "").strip():
            return False

        if self.peso_preferido_kg is not None:
            try:
                p = float(self.peso_preferido_kg)
            except (TypeError, ValueError):
                return False
            if not (0 < p <= 500):
                return False

        if self.altura_preferida_cm is not None:
            try:
                altura = float(self.altura_preferida_cm)
            except (TypeError, ValueError):
                return False
            if not (100 <= altura <= 250):
                return False

        if self.edad is not None:
            try:
                e = int(self.edad)
            except (TypeError, ValueError):
                return False
            if not (10 <= e <= 120):
                return False

        if self.sexo is not None and str(self.sexo).upper() not in SEXOS_VALIDOS:
            return False

        if self.fc_reposo is not None:
            try:
                fc = float(self.fc_reposo)
            except (TypeError, ValueError):
                return False
            if not (30 <= fc <= 220):
                return False

        return True

    def to_dict(self, incluir_sensible: bool = False) -> dict:
        """Willys_IA: Convierte la entidad a un diccionario serializable para JSON/Flask."""
        from dataclasses import asdict
        data = asdict(self)
        if not incluir_sensible:
            data.pop("password_hash", None)
            data.pop("token_verificacion", None)
            data.pop("token_expira", None)
            data.pop("reset_token", None)
            data.pop("reset_expira", None)
        data["email_verificado"] = bool(self.email_verificado)
        return data
