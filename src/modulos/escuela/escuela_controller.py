# -*- coding: utf-8 -*-
"""
Capa de Control (Controller Layer) — Módulo Escuela de Fútbol.
Willys_IA: Blueprint Flask que traduce HTTP a llamadas del servicio y
devuelve errores controlados (nunca un traceback crudo al usuario).

La app compartida usa una sola SQLite en la PC: cada dispositivo entra con
su propio usuario (ADMIN / ENTRENADOR / ALUMNO) y ve solo lo que su rol permite.
"""

import io
import os
import tempfile
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Tuple

from flask import (
    Blueprint,
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)

import database
from modulos.escuela.escuela_qr import generar_qr_svg
from modulos.escuela.escuela_service import Willys_IA_EscuelaService

bp_escuela = Blueprint("escuela", __name__)
servicio_escuela_singleton = Willys_IA_EscuelaService()

# Willys_IA: archivos de la PWA (están en src/static, fuera del dominio de calorías).
RUTA_STATIC = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "static")
)

CLAVES_SESION = (
    "escuela_usuario_id",
    "escuela_usuario",
    "escuela_nombre",
    "escuela_rol",
    "escuela_estudiante_id",
)


def _datos() -> Dict[str, Any]:
    """Acepta JSON o formulario, para probar con fetch o con curl."""
    return request.get_json(silent=True) or request.form.to_dict() or {}


def _error(mensaje: str, estado: int = 400) -> Tuple[Response, int]:
    return jsonify({"error": mensaje}), estado


def _estado_para(err: ValueError) -> int:
    """Distingue 'no existe' (404) de una regla de negocio (400)."""
    return 404 if "no existe" in str(err).lower() else 400


def usuario_actual() -> Dict[str, Any]:
    """Willys_IA: usuario de la app compartida, aislado del login de calorías."""
    if not session.get("escuela_usuario_id"):
        return None
    return {
        "id": session.get("escuela_usuario_id"),
        "usuario": session.get("escuela_usuario"),
        "nombre": session.get("escuela_nombre"),
        "rol": session.get("escuela_rol"),
        "estudiante_id": session.get("escuela_estudiante_id"),
    }


def requerir_login(vista):
    """API → 401 JSON; páginas → redirección al login de la escuela."""

    @wraps(vista)
    def envuelta(*args, **kwargs):
        if not usuario_actual():
            if request.path.startswith("/api/"):
                return _error("Inicia sesión en la app de la escuela.", 401)
            return redirect(url_for("escuela.login_escuela"))
        return vista(*args, **kwargs)

    return envuelta


def solo_roles(*roles):
    """Willys_IA: autorización por rol, aplicada también en el servidor."""

    def decorador(vista):
        @wraps(vista)
        def envuelta(*args, **kwargs):
            usuario = usuario_actual()
            if not usuario:
                if request.path.startswith("/api/"):
                    return _error("Inicia sesión en la app de la escuela.", 401)
                return redirect(url_for("escuela.login_escuela"))
            if usuario["rol"] not in roles:
                return _error("Tu rol no tiene permiso para esta acción.", 403)
            return vista(*args, **kwargs)

        return envuelta

    return decorador


# ----------------------------------------------------------------------
# Pantallas y acceso
# ----------------------------------------------------------------------


@bp_escuela.route("/escuela", methods=["GET"])
def pagina_escuela() -> str:
    """
    Panel compartido: admin y entrenador usan el mismo panel (laptop o celular).
    El alumno ve una pantalla propia de solo lectura.
    `?modo=local` conserva la demo aislada de IndexedDB (sin compartir datos).
    """
    if request.args.get("modo") == "local":
        return render_template("escuela.html", usuario=None)

    usuario = usuario_actual()
    if not usuario:
        return redirect(url_for("escuela.login_escuela"))
    if usuario["rol"] == "ALUMNO":
        return render_template("escuela_alumno.html", usuario=usuario)
    return render_template("escuela.html", usuario=usuario)


def _iniciar_sesion_escuela(usuario: Dict[str, Any]) -> None:
    """Guarda en la sesión los datos mínimos del usuario autenticado."""
    session["escuela_usuario_id"] = usuario["id"]
    session["escuela_usuario"] = usuario["usuario"]
    session["escuela_nombre"] = usuario["nombre"]
    session["escuela_rol"] = usuario["rol"]
    session["escuela_estudiante_id"] = usuario["estudiante_id"]


@bp_escuela.route("/escuela/login", methods=["GET", "POST"])
def login_escuela():
    """Acceso con las cuentas creadas en la app (sin credenciales demo)."""
    if not servicio_escuela_singleton.hay_usuarios():
        return redirect(url_for("escuela.setup_escuela"))

    if request.method == "POST":
        datos = _datos()
        usuario = servicio_escuela_singleton.autenticar(
            datos.get("usuario", ""), datos.get("clave", "")
        )
        if not usuario:
            return render_template(
                "escuela_login.html",
                error="Usuario o contraseña incorrectos.",
                usuario=datos.get("usuario", ""),
                hay_usuarios=True,
            ), 401

        _iniciar_sesion_escuela(usuario)
        return redirect(url_for("escuela.pagina_escuela"))

    return render_template(
        "escuela_login.html", error=None, usuario="", hay_usuarios=True
    )


@bp_escuela.route("/escuela/setup", methods=["GET", "POST"])
def setup_escuela():
    """
    Primer arranque: crea el administrador y el catálogo mínimo.
    Si ya hay cuentas, redirige al login para no abrir un segundo administrador.
    """
    if servicio_escuela_singleton.hay_usuarios():
        return redirect(url_for("escuela.login_escuela"))

    valores = {"usuario": "", "nombre": ""}
    if request.method == "POST":
        datos = _datos()
        valores = {
            "usuario": (datos.get("usuario") or "").strip(),
            "nombre": (datos.get("nombre") or "").strip(),
        }
        if (datos.get("clave") or "") != (datos.get("clave2") or ""):
            return render_template(
                "escuela_setup.html",
                error="Las contraseñas no coinciden.",
                valores=valores,
            ), 400
        try:
            usuario = servicio_escuela_singleton.crear_admin_inicial(
                usuario=datos.get("usuario", ""),
                nombre=datos.get("nombre", ""),
                clave=datos.get("clave", ""),
            )
        except ValueError as err:
            return render_template(
                "escuela_setup.html", error=str(err), valores=valores
            ), 400

        _iniciar_sesion_escuela(usuario)
        return redirect(url_for("escuela.pagina_escuela"))

    return render_template("escuela_setup.html", error=None, valores=valores)


@bp_escuela.route("/escuela/logout", methods=["GET", "POST"])
def logout_escuela():
    """Cierra solo la sesión de la escuela (no afecta la de calorías)."""
    for clave in CLAVES_SESION:
        session.pop(clave, None)
    return redirect(url_for("escuela.login_escuela"))


# ----------------------------------------------------------------------
# PWA: manifiesto, service worker e íconos
# ----------------------------------------------------------------------


@bp_escuela.route("/manifest.webmanifest", methods=["GET"])
def manifiesto_pwa() -> Response:
    """Datos de instalación: nombre, íconos y pantalla completa."""
    return send_from_directory(
        RUTA_STATIC, "manifest.webmanifest", mimetype="application/manifest+json"
    )


@bp_escuela.route("/sw.js", methods=["GET"])
def service_worker() -> Response:
    """Guarda los archivos de la app para abrirla sin internet."""
    respuesta = send_from_directory(RUTA_STATIC, "sw.js", mimetype="application/javascript")
    respuesta.headers["Service-Worker-Allowed"] = "/"
    respuesta.headers["Cache-Control"] = "no-cache"
    return respuesta


@bp_escuela.route("/icons/<nombre>", methods=["GET"])
def icono_pwa(nombre: str) -> Response:
    """Íconos de la pantalla de inicio del celular."""
    if nombre not in ("icon-192.png", "icon-512.png"):
        abort(404)
    return send_from_directory(os.path.join(RUTA_STATIC, "icons"), nombre, mimetype="image/png")


# ----------------------------------------------------------------------
# Contexto y sesiones
# ----------------------------------------------------------------------


@bp_escuela.route("/api/escuela/contexto", methods=["GET"])
@requerir_login
@solo_roles("ADMIN", "ENTRENADOR")
def api_contexto() -> Response:
    try:
        datos = servicio_escuela_singleton.contexto(request.args.get("periodo"))
        datos["usuario"] = usuario_actual()
        return jsonify(datos), 200
    except ValueError as err:
        return _error(str(err))


@bp_escuela.route("/api/escuela/mi", methods=["GET"])
@requerir_login
@solo_roles("ALUMNO")
def api_mi_registro() -> Response:
    """Willys_IA: vista de solo lectura del alumno sobre sus propios datos."""
    usuario = usuario_actual()
    try:
        return jsonify(
            servicio_escuela_singleton.mi_registro(
                usuario["estudiante_id"], request.args.get("periodo")
            )
        ), 200
    except ValueError as err:
        return _error(str(err), _estado_para(err))


@bp_escuela.route("/api/escuela/sesiones", methods=["GET", "POST"])
@requerir_login
@solo_roles("ADMIN", "ENTRENADOR")
def api_sesiones() -> Response:
    if request.method == "GET":
        try:
            fecha = request.args.get("fecha")
            return jsonify(
                {"sesiones": servicio_escuela_singleton.listar_sesiones(fecha=fecha)}
            ), 200
        except ValueError as err:
            return _error(str(err))

    datos = _datos()
    try:
        sesion = servicio_escuela_singleton.crear_sesion(
            sede_id=datos.get("sede_id"),
            categoria_id=datos.get("categoria_id"),
            fecha=datos.get("fecha", ""),
            hora=datos.get("hora", ""),
            entrenador=datos.get("entrenador", ""),
        )
        return jsonify({"sesion": sesion.to_dict(), "mensaje": "Sesión abierta"}), 201
    except ValueError as err:
        return _error(str(err))


@bp_escuela.route("/api/escuela/sesiones/<int:sesion_id>", methods=["GET"])
@requerir_login
@solo_roles("ADMIN", "ENTRENADOR")
def api_detalle_sesion(sesion_id: int) -> Response:
    try:
        return jsonify(servicio_escuela_singleton.detalle_sesion(sesion_id)), 200
    except ValueError as err:
        return _error(str(err), _estado_para(err))


@bp_escuela.route("/api/escuela/sesiones/<int:sesion_id>/asistencia", methods=["POST"])
@requerir_login
@solo_roles("ADMIN", "ENTRENADOR")
def api_registrar_asistencia(sesion_id: int) -> Response:
    datos = _datos()
    try:
        resultado = servicio_escuela_singleton.registrar_asistencia(
            sesion_id=sesion_id,
            qr_token=datos.get("qr_token"),
            estudiante_id=datos.get("estudiante_id"),
            metodo=datos.get("metodo", "QR"),
        )
        return jsonify(resultado), 201
    except ValueError as err:
        return _error(str(err), _estado_para(err))


@bp_escuela.route("/api/escuela/sesiones/<int:sesion_id>/avisos", methods=["POST"])
@requerir_login
@solo_roles("ADMIN", "ENTRENADOR")
def api_generar_avisos(sesion_id: int) -> Response:
    try:
        resultado = servicio_escuela_singleton.generar_avisos(sesion_id)
        return jsonify(resultado), 201
    except ValueError as err:
        return _error(str(err), _estado_para(err))


# ----------------------------------------------------------------------
# Avisos
# ----------------------------------------------------------------------


@bp_escuela.route("/api/escuela/avisos", methods=["GET"])
@requerir_login
@solo_roles("ADMIN", "ENTRENADOR")
def api_listar_avisos() -> Response:
    try:
        avisos = servicio_escuela_singleton.listar_avisos(request.args.get("estado"))
        return jsonify({"avisos": avisos}), 200
    except ValueError as err:
        return _error(str(err))


@bp_escuela.route("/api/escuela/avisos/<int:aviso_id>/enviado", methods=["POST"])
@requerir_login
@solo_roles("ADMIN")
def api_marcar_aviso(aviso_id: int) -> Response:
    try:
        return jsonify(servicio_escuela_singleton.marcar_aviso_enviado(aviso_id)), 200
    except ValueError as err:
        return _error(str(err), _estado_para(err))


# ----------------------------------------------------------------------
# Cobros (solo administración)
# ----------------------------------------------------------------------


@bp_escuela.route("/api/escuela/cobros", methods=["GET"])
@requerir_login
@solo_roles("ADMIN")
def api_listar_cobros() -> Response:
    try:
        return jsonify(servicio_escuela_singleton.listar_cobros(request.args.get("periodo", ""))), 200
    except ValueError as err:
        return _error(str(err))


@bp_escuela.route("/api/escuela/cobros", methods=["POST"])
@requerir_login
@solo_roles("ADMIN")
def api_marcar_pago() -> Response:
    datos = _datos()
    try:
        cobro = servicio_escuela_singleton.marcar_pago(
            estudiante_id=datos.get("estudiante_id"),
            periodo=datos.get("periodo", ""),
            estado=datos.get("estado", ""),
        )
        return jsonify({"cobro": cobro, "mensaje": "Estado de pago actualizado"}), 200
    except ValueError as err:
        return _error(str(err), _estado_para(err))


@bp_escuela.route("/api/escuela/resumen", methods=["GET"])
@requerir_login
@solo_roles("ADMIN", "ENTRENADOR")
def api_resumen() -> Response:
    try:
        return jsonify(servicio_escuela_singleton.resumen(request.args.get("periodo"))), 200
    except ValueError as err:
        return _error(str(err))


# ----------------------------------------------------------------------
# QR
# ----------------------------------------------------------------------


@bp_escuela.route("/api/escuela/estudiantes/<int:estudiante_id>/qr.svg", methods=["GET"])
@requerir_login
@solo_roles("ADMIN", "ENTRENADOR", "ALUMNO")
def api_qr_estudiante(estudiante_id: int) -> Response:
    usuario = usuario_actual()
    if usuario["rol"] == "ALUMNO" and usuario["estudiante_id"] != estudiante_id:
        return _error("Solo puedes ver tu propio código QR.", 403)

    estudiante = servicio_escuela_singleton.repositorio.obtener_estudiante(estudiante_id)
    if not estudiante:
        return _error("El estudiante no existe.", 404)
    respuesta = Response(generar_qr_svg(estudiante.qr_token), mimetype="image/svg+xml")
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


# ----------------------------------------------------------------------
# Altas, cuentas y catálogo (solo administración)
# ----------------------------------------------------------------------


@bp_escuela.route("/api/escuela/estudiantes", methods=["GET", "POST"])
@requerir_login
@solo_roles("ADMIN")
def api_estudiantes() -> Response:
    if request.method == "GET":
        return jsonify(
            {
                "estudiantes": [
                    e.to_dict()
                    for e in servicio_escuela_singleton.repositorio.listar_estudiantes()
                ]
            }
        ), 200

    datos = _datos()
    try:
        resultado = servicio_escuela_singleton.crear_estudiante(
            nombre=datos.get("nombre", ""),
            categoria_id=datos.get("categoria_id"),
            sede_id=datos.get("sede_id"),
            becado=datos.get("becado"),
            usuario=datos.get("usuario") or None,
            clave=datos.get("clave") or None,
        )
        return jsonify(
            {
                "estudiante": resultado["estudiante"],
                "cuenta": resultado["cuenta"],
                "mensaje": "Alumno registrado",
            }
        ), 201
    except ValueError as err:
        return _error(str(err), _estado_para(err))


@bp_escuela.route(
    "/api/escuela/estudiantes/<int:estudiante_id>/cuenta", methods=["POST"]
)
@requerir_login
@solo_roles("ADMIN")
def api_cuenta_alumno(estudiante_id: int) -> Response:
    datos = _datos()
    try:
        cuenta = servicio_escuela_singleton.crear_cuenta_alumno(
            estudiante_id, datos.get("usuario", ""), datos.get("clave", "")
        )
        return jsonify({"cuenta": cuenta, "mensaje": "Cuenta del alumno creada"}), 201
    except ValueError as err:
        return _error(str(err), _estado_para(err))


@bp_escuela.route(
    "/api/escuela/estudiantes/<int:estudiante_id>/baja", methods=["POST"]
)
@requerir_login
@solo_roles("ADMIN")
def api_baja_estudiante(estudiante_id: int) -> Response:
    try:
        resultado = servicio_escuela_singleton.dar_baja_estudiante(estudiante_id)
        return jsonify(
            {"estudiante": resultado, "mensaje": "Alumno dado de baja"}
        ), 200
    except ValueError as err:
        return _error(str(err), _estado_para(err))


@bp_escuela.route("/api/escuela/usuarios", methods=["GET", "POST"])
@requerir_login
@solo_roles("ADMIN")
def api_usuarios() -> Response:
    if request.method == "GET":
        return jsonify({"cuentas": servicio_escuela_singleton.listar_cuentas()}), 200

    datos = _datos()
    try:
        cuenta = servicio_escuela_singleton.crear_cuenta_personal(
            usuario=datos.get("usuario", ""),
            nombre=datos.get("nombre", ""),
            clave=datos.get("clave", ""),
            rol=datos.get("rol", "ENTRENADOR"),
        )
        return jsonify({"cuenta": cuenta, "mensaje": "Cuenta creada"}), 201
    except ValueError as err:
        return _error(str(err), _estado_para(err))


@bp_escuela.route("/api/escuela/usuarios/<usuario>/clave", methods=["POST"])
@requerir_login
@solo_roles("ADMIN")
def api_cambiar_clave(usuario: str) -> Response:
    datos = _datos()
    try:
        cuenta = servicio_escuela_singleton.cambiar_clave(
            usuario, datos.get("clave", "")
        )
        return jsonify({"cuenta": cuenta, "mensaje": "Contraseña actualizada"}), 200
    except ValueError as err:
        return _error(str(err), _estado_para(err))


@bp_escuela.route("/api/escuela/sedes", methods=["POST"])
@requerir_login
@solo_roles("ADMIN")
def api_crear_sede() -> Response:
    datos = _datos()
    try:
        sede = servicio_escuela_singleton.crear_sede(datos.get("nombre", ""))
        return jsonify({"sede": sede, "mensaje": "Sede creada"}), 201
    except ValueError as err:
        return _error(str(err), _estado_para(err))


@bp_escuela.route("/api/escuela/categorias", methods=["POST"])
@requerir_login
@solo_roles("ADMIN")
def api_crear_categoria() -> Response:
    datos = _datos()
    try:
        categoria = servicio_escuela_singleton.crear_categoria(
            datos.get("nombre", ""), datos.get("precio_mensual")
        )
        return jsonify({"categoria": categoria, "mensaje": "Categoría creada"}), 201
    except ValueError as err:
        return _error(str(err), _estado_para(err))


# ----------------------------------------------------------------------
# Respaldo y certificado de confianza
# ----------------------------------------------------------------------


@bp_escuela.route("/escuela/respaldo", methods=["GET"])
@requerir_login
@solo_roles("ADMIN")
def descargar_respaldo() -> Response:
    """
    Descarga una copia consistente de la SQLite.

    Se usa la API de backup de SQLite sobre un archivo temporal, así el
    respaldo es válido aunque un entrenador esté registrando asistencia
    en ese mismo momento.
    """
    ruta = database.obtener_ruta_db()
    if not os.path.exists(ruta):
        return _error("Todavía no existe una base de datos para respaldar.", 404)

    nombre = "escuela-respaldo-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".db"
    descriptor, temporal = tempfile.mkstemp(prefix="respaldo-escuela-", suffix=".db")
    os.close(descriptor)
    try:
        database.crear_respaldo(temporal)
        with open(temporal, "rb") as archivo:
            contenido = archivo.read()
    finally:
        try:
            os.remove(temporal)
        except OSError:
            pass

    return send_file(
        io.BytesIO(contenido),
        as_attachment=True,
        download_name=nombre,
        mimetype="application/x-sqlite3",
    )


@bp_escuela.route("/ca.crt", methods=["GET"])
def descargar_ca() -> Response:
    """Certificado de la CA local para instalarlo en los celulares."""
    from certificados import RUTA_CA

    if not os.path.exists(RUTA_CA):
        return _error("El certificado HTTPS todavía no fue generado.", 404)
    return send_file(RUTA_CA, as_attachment=True, download_name="escuela-ca.crt")
