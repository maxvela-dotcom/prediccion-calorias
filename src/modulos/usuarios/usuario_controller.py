# -*- coding: utf-8 -*-
"""
Capa de Control y Endpoints Web Flask de Usuarios (Controller Layer).
Willys_IA: Patrón Controlador / REST Controller.
Coordina las peticiones HTTP del módulo de usuarios delegando en la capa de servicio
y retornando respuestas JSON defensivas.
"""

from typing import List, Optional
from flask import Blueprint, request, jsonify, session, Response
from modulos.usuarios.usuario_service import Willys_IA_UsuarioService
from modulos.usuarios.usuario_model import Willys_IA_UsuarioModel
from security import client_ip, rate_limit, exigir_csrf_json


class Willys_IA_UsuarioController:
    """
    Willys_IA: Controlador que recibe peticiones para el módulo de usuarios
    y maneja defensivamente los errores sin romper la consola o el servidor.
    """

    def __init__(self, servicio: Optional[Willys_IA_UsuarioService] = None):
        """Inicializa inyectando el servicio de usuarios."""
        self._servicio = servicio if servicio is not None else Willys_IA_UsuarioService()

    @property
    def servicio(self) -> Willys_IA_UsuarioService:
        """Acceso de lectura a la capa de servicio."""
        return self._servicio

    def registrar(
        self,
        nombre: str,
        email: str,
        password: str,
        rol: str = "ESTUDIANTE",
        peso_preferido_kg=None,
        edad=None,
        sexo=None,
        fc_reposo=None,
    ) -> Optional[Willys_IA_UsuarioModel]:
        """
        Willys_IA: Registra un usuario y maneja excepciones controladas.
        """
        try:
            user = self._servicio.registrar_usuario(
                nombre, email, password, rol,
                peso_preferido_kg=peso_preferido_kg,
                edad=edad,
                sexo=sexo,
                fc_reposo=fc_reposo,
            )
            print(f"\n[ÉXITO Willys_IA]: Usuario #{user.id} '{user.nombre_completo}' ({user.rol}) registrado correctamente.")
            return user
        except ValueError as err:
            print(f"\n[ALERTA Willys_IA]: {err}")
            return None

    def listar(self) -> List[Willys_IA_UsuarioModel]:
        """
        Willys_IA: Retorna la lista de usuarios y la despliega formateada en consola.
        """
        usuarios = self._servicio.listar_usuarios()
        return usuarios


# ============================================================================
# ENDPOINTS REST CON FLASK BLUEPRINT (Willys_IA)
# Equivalente en Spring Boot a un @RestController en /api/usuarios
# ============================================================================

bp_usuarios = Blueprint("usuarios", __name__, url_prefix="/api/usuarios")
controlador_usuarios_singleton = Willys_IA_UsuarioController()

LIMITE_REGISTRO = 10      # registros
VENTANA_REGISTRO = 600    # segundos


@bp_usuarios.route("", methods=["GET"])
def api_listar_usuarios() -> Response:
    """
    /** Endpoint GET: Lista todos los usuarios registrados. */
    Willys_IA: Datos internos; requiere sesión para no filtrar correos/roles.
    """
    if not session.get("usuario_id"):
        return jsonify({"error": "No autenticado."}), 401
    usuarios = controlador_usuarios_singleton.listar()
    return jsonify([u.to_dict() for u in usuarios]), 200


@bp_usuarios.route("", methods=["POST"])
def api_registrar_usuario() -> Response:
    """
    /** Endpoint POST: Registra un nuevo usuario en el sistema. */
    Willys_IA: Valida formato de correo, contraseña, rol y regla de unicidad en el Service.
    Es un endpoint público (no requiere sesión); se limita por IP contra abuso.
    """
    if not rate_limit(f"api_usuarios_post:{client_ip()}", LIMITE_REGISTRO, VENTANA_REGISTRO):
        return jsonify({"error": "Demasiados registros desde esta IP. Intenta más tarde."}), 429

    datos = request.get_json(silent=True) or request.form.to_dict()
    if not datos:
        return jsonify({"error": "Debe enviar un payload JSON o formulario válido."}), 400

    nombre = datos.get("nombre") or datos.get("nombre_completo", "")
    email = datos.get("email", "")
    password = datos.get("password", "")
    rol = datos.get("rol", "ESTUDIANTE")

    try:
        nuevo_usuario = controlador_usuarios_singleton.servicio.registrar_usuario(
            nombre=nombre,
            email=email,
            password=password,
            rol=rol,
            peso_preferido_kg=datos.get("peso_preferido_kg"),
            edad=datos.get("edad"),
            sexo=datos.get("sexo"),
            fc_reposo=datos.get("fc_reposo"),
        )
        return jsonify(nuevo_usuario.to_dict()), 201
    except ValueError as err:
        return jsonify({"error": str(err)}), 400


@bp_usuarios.route("/<int:id_usuario>/baja", methods=["POST"])
def api_dar_baja_usuario(id_usuario: int) -> Response:
    """
    /** Endpoint POST: Da de baja un usuario cambiando su estado a INACTIVO. */
    Willys_IA: Requiere sesión + CSRF. Un usuario solo puede darse de baja a sí
    mismo; un ADMIN puede dar de baja a cualquier usuario.
    """
    uid = session.get("usuario_id")
    if not uid:
        return jsonify({"error": "No autenticado."}), 401

    error_csrf = exigir_csrf_json()
    if error_csrf is not None:
        cuerpo, estado = error_csrf
        return jsonify(cuerpo), estado

    actor = controlador_usuarios_singleton.servicio.buscar_por_id(int(uid))
    if not actor:
        session.clear()
        return jsonify({"error": "No autenticado."}), 401

    if id_usuario != actor.id and (actor.rol or "").upper() != "ADMIN":
        return jsonify({"error": "No autorizado para dar de baja a otro usuario."}), 403

    try:
        ok = controlador_usuarios_singleton.servicio.dar_de_baja(id_usuario)
        return jsonify({
            "mensaje": f"Usuario #{id_usuario} dado de baja correctamente.",
            "id": id_usuario,
            "estado": "INACTIVO",
            "exito": ok
        }), 200
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
