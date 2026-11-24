# -*- coding: utf-8 -*-
"""
Capa de Control / Endpoints de Predicción de Calorías (Controller Layer).
Willys_IA: Blueprint Flask para registrar, listar y exportar predicciones
del usuario autenticado, con CSRF en JSON y rate limiting.
"""

from typing import Optional
from flask import Blueprint, request, jsonify, session, Response
from modulos.prediccion_calorias.caloria_service import Willys_IA_CaloriaService
from modulos.usuarios.usuario_service import Willys_IA_UsuarioService
from security import exigir_csrf_json, rate_limit


class Willys_IA_CaloriaController:
    def __init__(self, servicio: Optional[Willys_IA_CaloriaService] = None):
        self._servicio = servicio if servicio is not None else Willys_IA_CaloriaService()

    @property
    def servicio(self) -> Willys_IA_CaloriaService:
        return self._servicio


bp_calorias = Blueprint("calorias", __name__, url_prefix="/api/calorias")
controlador_calorias_singleton = Willys_IA_CaloriaController()
servicio_usuarios = Willys_IA_UsuarioService()

LIMITE_POST = 30        # solicitudes
VENTANA_POST = 60       # segundos
LIMITE_DELETE = 30      # movimientos a papelera por usuario
VENTANA_DELETE = 60     # segundos
LIMITE_RESTAURAR = 30   # restauraciones por usuario
VENTANA_RESTAURAR = 60  # segundos
LIMITE_PURGA = 10       # borrados definitivos / vaciados por usuario
VENTANA_PURGA = 60      # segundos
LIMITE_ANALISIS = 30    # consultas de análisis técnico por usuario
VENTANA_ANALISIS = 60   # segundos


def _usuario_autenticado_id() -> Optional[int]:
    uid = session.get("usuario_id")
    return int(uid) if uid is not None else None


def _respuesta_paginada(resultado: dict) -> tuple:
    """Contrato JSON compartido por historial activo y papelera."""
    servicio = controlador_calorias_singleton.servicio
    return jsonify({
        "items": [servicio.serializar(i) for i in resultado["items"]],
        "total": resultado["total"],
        "page": resultado["page"],
        "per_page": resultado["per_page"],
        "total_pages": resultado["total_pages"],
        "total_calorias": resultado["total_calorias"],
    }), 200


@bp_calorias.route("/analisis", methods=["GET"])
def api_analisis_regresion() -> Response:
    """Análisis técnico del modelo entrenado desde el CSV (requiere sesión)."""
    uid = _usuario_autenticado_id()
    if not uid:
        return jsonify({"error": "No autenticado."}), 401
    if not rate_limit(f"calorias_analisis:{uid}", LIMITE_ANALISIS, VENTANA_ANALISIS):
        return jsonify({"error": "Demasiadas solicitudes. Intenta nuevamente en un minuto."}), 429
    try:
        return jsonify(controlador_calorias_singleton.servicio.analisis()), 200
    except ValueError as err:
        return jsonify({"error": str(err)}), 500


@bp_calorias.route("", methods=["GET"])
def api_listar_predicciones() -> Response:
    uid = _usuario_autenticado_id()
    if not uid:
        return jsonify({"error": "No autenticado."}), 401
    q = request.args.get("q")
    actividad = request.args.get("actividad")
    page = request.args.get("page", 1)
    per_page = request.args.get("per_page", 20)
    resultado = controlador_calorias_singleton.servicio.listar_paginado(
        uid, q=q, actividad=actividad, page=page, per_page=per_page
    )
    return _respuesta_paginada(resultado)


@bp_calorias.route("", methods=["POST"])
def api_crear_prediccion() -> Response:
    uid = _usuario_autenticado_id()
    if not uid:
        return jsonify({"error": "No autenticado."}), 401

    error_csrf = exigir_csrf_json()
    if error_csrf is not None:
        cuerpo, estado = error_csrf
        return jsonify(cuerpo), estado

    if not rate_limit(f"calorias_post:{uid}", LIMITE_POST, VENTANA_POST):
        return jsonify({"error": "Demasiadas solicitudes. Intenta nuevamente en un minuto."}), 429

    datos = request.get_json(silent=True) or request.form.to_dict()
    if not datos:
        return jsonify({"error": "Debe enviar un payload JSON o formulario válido."}), 400

    try:
        peso_kg = float(datos.get("peso_kg", 0))
        duracion_min = float(datos.get("duracion_min", 0))
        met = float(datos.get("met", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "peso_kg, duracion_min y met deben ser números válidos."}), 400

    # El perfil es la fuente de verdad para edad/sexo; el payload puede completar.
    perfil = servicio_usuarios.buscar_por_id(uid)
    edad = perfil.edad if perfil and perfil.edad is not None else datos.get("edad")
    sexo = perfil.sexo if perfil and perfil.sexo is not None else datos.get("sexo")
    fc_promedio = datos.get("fc_promedio")
    altura_cm = datos.get("altura_cm")
    if altura_cm in (None, ""):
        altura_cm = perfil.altura_preferida_cm if perfil else None

    tipo_actividad = datos.get("tipo_actividad", "")
    try:
        item = controlador_calorias_singleton.servicio.predecir_y_guardar(
            usuario_id=uid,
            tipo_actividad=tipo_actividad,
            peso_kg=peso_kg,
            duracion_min=duracion_min,
            met=met,
            fc_promedio=fc_promedio,
            edad=edad,
            sexo=sexo,
            altura_cm=altura_cm,
        )
        return jsonify(controlador_calorias_singleton.servicio.serializar(item)), 201
    except ValueError as err:
        return jsonify({"error": str(err)}), 400


@bp_calorias.route("/<int:registro_id>", methods=["GET"])
def api_obtener_prediccion(registro_id: int) -> Response:
    """Devuelve un registro propio con el desglose (incluye los de la papelera)."""
    uid = _usuario_autenticado_id()
    if not uid:
        return jsonify({"error": "No autenticado."}), 401
    item = controlador_calorias_singleton.servicio.obtener_registro(
        uid, registro_id, incluir_eliminados=True
    )
    if item is None:
        return jsonify({"error": "Registro no encontrado."}), 404
    return jsonify(controlador_calorias_singleton.servicio.serializar(item)), 200


@bp_calorias.route("/<int:registro_id>", methods=["DELETE"])
def api_eliminar_prediccion(registro_id: int) -> Response:
    """Mueve una predicción del historial a la papelera del usuario autenticado."""
    uid = _usuario_autenticado_id()
    if not uid:
        return jsonify({"error": "No autenticado."}), 401

    error_csrf = exigir_csrf_json()
    if error_csrf is not None:
        cuerpo, estado = error_csrf
        return jsonify(cuerpo), estado

    if not rate_limit(f"calorias_delete:{uid}", LIMITE_DELETE, VENTANA_DELETE):
        return jsonify({"error": "Demasiadas solicitudes. Intenta nuevamente en un minuto."}), 429

    try:
        eliminado = controlador_calorias_singleton.servicio.eliminar_registro(uid, registro_id)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    if not eliminado:
        return jsonify({"error": "Registro no encontrado."}), 404
    return jsonify({
        "eliminado": True,
        "en_papelera": True,
        "id": registro_id,
        "mensaje": "El registro se movió a la papelera; puedes restaurarlo.",
    }), 200


@bp_calorias.route("/papelera", methods=["GET"])
def api_listar_papelera() -> Response:
    """Lista la papelera del usuario con el mismo contrato paginado del historial."""
    uid = _usuario_autenticado_id()
    if not uid:
        return jsonify({"error": "No autenticado."}), 401
    resultado = controlador_calorias_singleton.servicio.listar_papelera_paginado(
        uid,
        q=request.args.get("q"),
        actividad=request.args.get("actividad"),
        page=request.args.get("page", 1),
        per_page=request.args.get("per_page", 20),
    )
    return _respuesta_paginada(resultado)


@bp_calorias.route("/papelera", methods=["DELETE"])
def api_vaciar_papelera() -> Response:
    """Elimina definitivamente todos los registros en papelera del usuario."""
    uid = _usuario_autenticado_id()
    if not uid:
        return jsonify({"error": "No autenticado."}), 401

    error_csrf = exigir_csrf_json()
    if error_csrf is not None:
        cuerpo, estado = error_csrf
        return jsonify(cuerpo), estado

    if not rate_limit(f"calorias_vaciar:{uid}", LIMITE_PURGA, VENTANA_PURGA):
        return jsonify({"error": "Demasiadas solicitudes. Intenta nuevamente en un minuto."}), 429

    cantidad = controlador_calorias_singleton.servicio.vaciar_papelera(uid)
    return jsonify({
        "eliminados": cantidad,
        "mensaje": f"Se borraron definitivamente {cantidad} registro(s).",
    }), 200


@bp_calorias.route("/<int:registro_id>/restaurar", methods=["POST"])
def api_restaurar_prediccion(registro_id: int) -> Response:
    """Restaura un registro propio desde la papelera al historial activo."""
    uid = _usuario_autenticado_id()
    if not uid:
        return jsonify({"error": "No autenticado."}), 401

    error_csrf = exigir_csrf_json()
    if error_csrf is not None:
        cuerpo, estado = error_csrf
        return jsonify(cuerpo), estado

    if not rate_limit(f"calorias_restaurar:{uid}", LIMITE_RESTAURAR, VENTANA_RESTAURAR):
        return jsonify({"error": "Demasiadas solicitudes. Intenta nuevamente en un minuto."}), 429

    try:
        restaurado = controlador_calorias_singleton.servicio.restaurar_registro(uid, registro_id)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    if not restaurado:
        return jsonify({"error": "Registro no encontrado en la papelera."}), 404

    item = controlador_calorias_singleton.servicio.obtener_registro(uid, registro_id)
    return jsonify({
        "restaurado": True,
        "id": registro_id,
        "registro": controlador_calorias_singleton.servicio.serializar(item) if item else None,
        "mensaje": "El registro volvió a tu historial.",
    }), 200


@bp_calorias.route("/<int:registro_id>/definitivo", methods=["DELETE"])
def api_eliminar_definitivamente(registro_id: int) -> Response:
    """Borra de SQLite un registro propio que ya está en la papelera."""
    uid = _usuario_autenticado_id()
    if not uid:
        return jsonify({"error": "No autenticado."}), 401

    error_csrf = exigir_csrf_json()
    if error_csrf is not None:
        cuerpo, estado = error_csrf
        return jsonify(cuerpo), estado

    if not rate_limit(f"calorias_definitivo:{uid}", LIMITE_PURGA, VENTANA_PURGA):
        return jsonify({"error": "Demasiadas solicitudes. Intenta nuevamente en un minuto."}), 429

    try:
        eliminado = controlador_calorias_singleton.servicio.eliminar_definitivamente(uid, registro_id)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    if not eliminado:
        return jsonify({"error": "Registro no encontrado en la papelera."}), 404
    return jsonify({
        "eliminado_definitivamente": True,
        "id": registro_id,
        "mensaje": "El registro se borró definitivamente.",
    }), 200


@bp_calorias.route("/export.csv", methods=["GET"])
def api_exportar_csv() -> Response:
    """Descarga el historial del usuario autenticado en CSV (respeta filtros)."""
    uid = _usuario_autenticado_id()
    if not uid:
        return jsonify({"error": "No autenticado."}), 401

    q = request.args.get("q")
    actividad = request.args.get("actividad")
    csv_texto = controlador_calorias_singleton.servicio.exportar_csv(uid, q=q, actividad=actividad)
    nombre = f"historial_calorias_{uid}.csv"
    return Response(
        "\ufeff" + csv_texto,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
