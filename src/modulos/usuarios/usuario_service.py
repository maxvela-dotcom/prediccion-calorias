# -*- coding: utf-8 -*-
"""
Capa de Lógica de Negocio de Usuarios (Service Layer).
Willys_IA: Patrón de Servicio para Usuarios.
Valida reglas de negocio: unicidad de correo, formato, contraseña, roles,
perfil ampliado (edad/sexo/FC), verificación de correo y recuperación de contraseña.
"""

import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from modulos.usuarios.usuario_model import Willys_IA_UsuarioModel, SEXOS_VALIDOS
from modulos.usuarios.usuario_repository import Willys_IA_UsuarioRepository
from security import generar_token

FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"
HORAS_VERIFICACION = 24
MINUTOS_RESET = 60


def _ahora() -> datetime:
    return datetime.now()


def _formatear(dt: datetime) -> str:
    return dt.strftime(FORMATO_FECHA)


def _expirado(valor: Optional[str]) -> bool:
    if not valor:
        return True
    try:
        return datetime.strptime(valor, FORMATO_FECHA) < _ahora()
    except (TypeError, ValueError):
        return True


def _normalizar_sexo(valor) -> Optional[str]:
    if valor in (None, ""):
        return None
    texto = str(valor).strip().upper()
    equivalencias = {
        "M": "M",
        "MASCULINO": "M",
        "HOMBRE": "M",
        "F": "F",
        "FEMENINO": "F",
        "MUJER": "F",
        "OTRO": "OTRO",
        "OTRA": "OTRO",
        "X": "OTRO",
    }
    return equivalencias.get(texto, texto if texto in SEXOS_VALIDOS else "INVALIDO")


class Willys_IA_UsuarioService:
    """
    Willys_IA: Orquestador de la lógica de usuarios y autenticación básica.
    """

    def __init__(self, repositorio: Optional[Willys_IA_UsuarioRepository] = None):
        """Inyecta el repositorio de usuarios."""
        self._repo = repositorio if repositorio is not None else Willys_IA_UsuarioRepository()

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    @staticmethod
    def _validar_password(password: str) -> str:
        password_texto = password or ""
        if len(password_texto) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        if not any(c.isalpha() for c in password_texto) or not any(c.isdigit() for c in password_texto):
            raise ValueError("La contraseña debe incluir al menos una letra y un número.")
        return password_texto

    @staticmethod
    def _parse_peso(valor) -> Optional[float]:
        if valor in (None, ""):
            return None
        try:
            peso = float(valor)
        except (TypeError, ValueError):
            raise ValueError("El peso preferido debe ser un número válido.")
        if not (0 < peso <= 500):
            raise ValueError("El peso preferido debe ser mayor a 0 y menor o igual a 500 kg.")
        return peso

    @staticmethod
    def _parse_altura(valor) -> Optional[float]:
        if valor in (None, ""):
            return None
        try:
            altura = float(valor)
        except (TypeError, ValueError):
            raise ValueError("La altura preferida debe ser un número válido.")
        if not (100 <= altura <= 250):
            raise ValueError("La altura debe estar entre 100 y 250 cm.")
        return altura

    @staticmethod
    def _parse_edad(valor) -> Optional[int]:
        if valor in (None, ""):
            return None
        try:
            edad = int(valor)
        except (TypeError, ValueError):
            raise ValueError("La edad debe ser un número entero.")
        if not (10 <= edad <= 120):
            raise ValueError("La edad debe estar entre 10 y 120 años.")
        return edad

    @staticmethod
    def _parse_fc_reposo(valor) -> Optional[float]:
        if valor in (None, ""):
            return None
        try:
            fc = float(valor)
        except (TypeError, ValueError):
            raise ValueError("La frecuencia cardíaca de reposo debe ser un número.")
        if not (30 <= fc <= 220):
            raise ValueError("La FC de reposo debe estar entre 30 y 220 ppm.")
        return fc

    @staticmethod
    def _parse_sexo(valor) -> Optional[str]:
        sexo = _normalizar_sexo(valor)
        if sexo == "INVALIDO" or (sexo is not None and sexo not in SEXOS_VALIDOS):
            raise ValueError("El sexo debe ser 'M', 'F' u 'OTRO'.")
        return sexo

    # ------------------------------------------------------------------
    # Registro y autenticación
    # ------------------------------------------------------------------

    def registrar_usuario(
        self,
        nombre: str,
        email: str,
        password: str,
        rol: str = "ESTUDIANTE",
        peso_preferido_kg=None,
        edad=None,
        sexo=None,
        fc_reposo=None,
    ) -> Willys_IA_UsuarioModel:
        """
        Willys_IA: Registra un usuario aplicando las reglas:
        - Nombre válido (mínimo 3 caracteres).
        - Correo con formato válido y único.
        - Contraseña segura (mínimo 8 caracteres, debe incluir letras y números).
        - Rol válido y datos de perfil opcionales en rango válido.

        Lanza ValueError si viola alguna regla; retorna el usuario guardado.
        """
        nombre_limpio = (nombre or "").strip()
        email_limpio = (email or "").strip().lower()
        rol_limpio = (rol or "ESTUDIANTE").strip().upper()
        password_texto = self._validar_password(password)

        peso = self._parse_peso(peso_preferido_kg)
        edad_val = self._parse_edad(edad)
        sexo_val = self._parse_sexo(sexo)
        fc_val = self._parse_fc_reposo(fc_reposo)

        usuario = Willys_IA_UsuarioModel(
            id=0,
            nombre_completo=nombre_limpio,
            email=email_limpio,
            password_hash=generate_password_hash(password_texto),
            rol=rol_limpio,
            estado="ACTIVO",
            peso_preferido_kg=peso,
            edad=edad_val,
            sexo=sexo_val,
            fc_reposo=fc_val,
        )

        if not usuario.validar():
            raise ValueError("Datos de usuario inválidos: verifique nombre (>= 3 caracteres), correo y rol válido.")

        # Regla de Negocio: Unicidad de Correo
        existente = self._repo.obtener_por_email(email_limpio)
        if existente:
            raise ValueError(f"Ya existe un usuario registrado con el correo '{email_limpio}'.")

        return self._repo.guardar(usuario)

    def autenticar(self, email: str, password: str) -> Willys_IA_UsuarioModel:
        """
        Willys_IA: Verifica credenciales de acceso.
        - El usuario debe existir, estar ACTIVO y la contraseña debe coincidir.
        """
        email_limpio = (email or "").strip().lower()
        password_texto = password or ""
        usuario = self._repo.obtener_por_email(email_limpio)
        if not usuario:
            raise ValueError("Credenciales inválidas.")
        if usuario.estado.upper() != "ACTIVO":
            raise ValueError("El usuario se encuentra inactivo.")
        if not check_password_hash(usuario.password_hash, password_texto):
            raise ValueError("Credenciales inválidas.")
        return usuario

    def autenticar_google(self, claims: dict) -> Willys_IA_UsuarioModel:
        """
        Inicia sesión con una cuenta de Google verificada.

        - Busca primero por `google_sub` (identificador estable de Google).
        - Si no existe, vincula por correo verificado con un usuario local,
          conservando su historial y su contraseña actual.
        - Si el correo no existe, crea la cuenta con una contraseña aleatoria
          desconocida: el acceso seguirá siendo solo mediante Google.
        """
        datos = claims or {}
        sub = str(datos.get("sub") or "").strip()
        email = str(datos.get("email") or "").strip().lower()
        nombre = str(datos.get("nombre") or datos.get("name") or "").strip()

        if not sub or "@" not in email or "." not in email:
            raise ValueError("La cuenta de Google no entregó un correo válido.")
        if not datos.get("email_verificado"):
            raise ValueError("Google no confirmó el correo de la cuenta.")

        if len(nombre) < 3:
            nombre = email.split("@")[0]
        if len(nombre) < 3:
            nombre = "Usuario Google"

        por_sub = self._repo.obtener_por_google_sub(sub)
        if por_sub:
            if por_sub.estado.upper() != "ACTIVO":
                raise ValueError("El usuario se encuentra inactivo.")
            return por_sub

        existente = self._repo.obtener_por_email(email)
        if existente:
            if existente.google_sub and existente.google_sub != sub:
                raise ValueError(
                    "Ese correo ya está vinculado a otra cuenta de Google."
                )
            if existente.estado.upper() != "ACTIVO":
                raise ValueError("El usuario se encuentra inactivo.")
            if not self._repo.vincular_google(existente.id, sub):
                raise ValueError("No se pudo vincular la cuenta de Google.")
            return self._repo.obtener_por_id(existente.id)

        usuario = Willys_IA_UsuarioModel(
            id=0,
            nombre_completo=nombre,
            email=email,
            # Contraseña imposible de adivinar: la cuenta solo entra con Google.
            password_hash=generate_password_hash(secrets.token_urlsafe(32)),
            rol="ESTUDIANTE",
            estado="ACTIVO",
            email_verificado=1,
            proveedor="GOOGLE",
            google_sub=sub,
        )
        if not usuario.validar():
            raise ValueError("Datos de usuario de Google inválidos.")

        try:
            return self._repo.guardar(usuario)
        except sqlite3.IntegrityError:
            # Carrera entre dos callbacks simultáneos con el mismo sub.
            creado = self._repo.obtener_por_google_sub(sub)
            if creado:
                return creado
            raise ValueError("Ya existe un usuario registrado con ese correo.")

    def listar_usuarios(self) -> List[Willys_IA_UsuarioModel]:
        """Willys_IA: Retorna todos los usuarios registrados."""
        return self._repo.obtener_todos()

    def buscar_por_id(self, id_usuario: int) -> Optional[Willys_IA_UsuarioModel]:
        """Willys_IA: Busca un usuario por ID."""
        return self._repo.obtener_por_id(id_usuario)

    def dar_de_baja(self, id_usuario: int) -> bool:
        """Willys_IA: Cambia el estado de un usuario a INACTIVO."""
        usuario = self._repo.obtener_por_id(id_usuario)
        if not usuario:
            raise ValueError(f"No existe usuario con ID #{id_usuario}.")
        return self._repo.cambiar_estado(id_usuario, "INACTIVO")

    # ------------------------------------------------------------------
    # Perfil
    # ------------------------------------------------------------------

    def actualizar_perfil(
        self,
        id_usuario: int,
        peso_preferido_kg=None,
        altura_preferida_cm=None,
        edad=None,
        sexo=None,
        fc_reposo=None,
        campos: Optional[dict] = None,
    ) -> Willys_IA_UsuarioModel:
        """
        Actualiza el perfil del usuario.

        - Si `campos` se entrega, solo se actualizan las claves presentes
          (permite cambios parciales y limpiar valores con None).
        - Si no, se actualiza el peso y, cuando se envían, edad/sexo/FC.
        """
        usuario = self._repo.obtener_por_id(id_usuario)
        if not usuario:
            raise ValueError(f"No existe usuario con ID #{id_usuario}.")

        if campos is None:
            campos = {"peso_preferido_kg": peso_preferido_kg}
            if altura_preferida_cm is not None:
                campos["altura_preferida_cm"] = altura_preferida_cm
            if edad is not None:
                campos["edad"] = edad
            if sexo is not None:
                campos["sexo"] = sexo
            if fc_reposo is not None:
                campos["fc_reposo"] = fc_reposo

        limpios = {}
        if "peso_preferido_kg" in campos:
            limpios["peso_preferido_kg"] = self._parse_peso(campos.get("peso_preferido_kg"))
        if "altura_preferida_cm" in campos:
            limpios["altura_preferida_cm"] = self._parse_altura(
                campos.get("altura_preferida_cm")
            )
        if "edad" in campos:
            limpios["edad"] = self._parse_edad(campos.get("edad"))
        if "sexo" in campos:
            limpios["sexo"] = self._parse_sexo(campos.get("sexo"))
        if "fc_reposo" in campos:
            limpios["fc_reposo"] = self._parse_fc_reposo(campos.get("fc_reposo"))

        actualizado = self._repo.actualizar_perfil(id_usuario, limpios)
        if not actualizado:
            raise ValueError("No se pudo actualizar el perfil.")
        return actualizado

    # ------------------------------------------------------------------
    # Verificación de correo (token de un solo uso)
    # ------------------------------------------------------------------

    def generar_verificacion(self, id_usuario: int) -> str:
        """Genera y guarda un token de verificación de correo (24 h)."""
        usuario = self._repo.obtener_por_id(id_usuario)
        if not usuario:
            raise ValueError(f"No existe usuario con ID #{id_usuario}.")
        token = generar_token()
        expira = _formatear(_ahora() + timedelta(hours=HORAS_VERIFICACION))
        if not self._repo.guardar_token_verificacion(id_usuario, token, expira):
            raise ValueError("No se pudo generar el token de verificación.")
        return token

    def verificar_email(self, token: str) -> Willys_IA_UsuarioModel:
        """Consume el token de verificación y marca el correo como verificado."""
        usuario = self._repo.obtener_por_token_verificacion(token)
        if not usuario:
            raise ValueError("Token de verificación inválido o ya utilizado.")
        if _expirado(usuario.token_expira):
            raise ValueError("El token de verificación expiró. Solicita uno nuevo.")
        if not self._repo.marcar_email_verificado(usuario.id):
            raise ValueError("No se pudo verificar el correo.")
        return self._repo.obtener_por_id(usuario.id)

    def marcar_email_verificado(self, id_usuario: int) -> bool:
        """Marca el correo como verificado (usado para usuarios semilla/demostración)."""
        return self._repo.marcar_email_verificado(id_usuario)

    # ------------------------------------------------------------------
    # Recuperación de contraseña (token de un solo uso)
    # ------------------------------------------------------------------

    def solicitar_reset(self, email: str) -> Optional[str]:
        """
        Genera un token de recuperación (60 min) si el correo existe.
        Retorna None si no existe, sin revelar esa condición al cliente.
        """
        usuario = self._repo.obtener_por_email((email or "").strip().lower())
        if not usuario:
            return None
        token = generar_token()
        expira = _formatear(_ahora() + timedelta(minutes=MINUTOS_RESET))
        if not self._repo.guardar_token_reset(usuario.id, token, expira):
            return None
        return token

    def token_reset_valido(self, token: str) -> bool:
        """Indica si el token de recuperación existe y no expiró."""
        usuario = self._repo.obtener_por_token_reset(token)
        return bool(usuario and not _expirado(usuario.reset_expira))

    def restablecer_password(self, token: str, nueva_password: str) -> Willys_IA_UsuarioModel:
        """Valida el token y actualiza la contraseña (token de un solo uso)."""
        usuario = self._repo.obtener_por_token_reset(token)
        if not usuario:
            raise ValueError("Token de recuperación inválido o ya utilizado.")
        if _expirado(usuario.reset_expira):
            raise ValueError("El token de recuperación expiró. Solicita uno nuevo.")
        password_texto = self._validar_password(nueva_password)
        if not self._repo.actualizar_password(usuario.id, generate_password_hash(password_texto)):
            raise ValueError("No se pudo actualizar la contraseña.")
        return self._repo.obtener_por_id(usuario.id)
