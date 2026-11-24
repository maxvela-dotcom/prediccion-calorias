# -*- coding: utf-8 -*-
"""
Capa de Control y Endpoints Web Flask del MVP (Controller Layer).
Willys_IA: Patrón Controlador / REST Controller.
Traduce las peticiones HTTP (Flask) en llamadas a la capa de servicio
y maneja las excepciones defensivamente devolviendo respuestas JSON estandarizadas.
"""

from typing import List, Optional, Dict, Any
from flask import Blueprint, request, jsonify, Response
from modulos.gestion_mvp.mvp_service import Willys_IA_ItemService
from modulos.gestion_mvp.mvp_model import Willys_IA_ItemModel


class Willys_IA_ItemController:
    """
    Willys_IA: Controlador de lógica y presentación para el Producto Mínimo Viable.
    Coordina las interacciones entre las rutas web/consola y el servicio de negocio.
    """

    def __init__(self, servicio: Optional[Willys_IA_ItemService] = None):
        """Inicializa inyectando la capa de servicio."""
        self._servicio = servicio if servicio is not None else Willys_IA_ItemService()

    @property
    def servicio(self) -> Willys_IA_ItemService:
        """Acceso de lectura a la capa de servicio."""
        return self._servicio

    def registrar(self, nombre: str, categoria: str, valor: float) -> Optional[Willys_IA_ItemModel]:
        """
        Willys_IA: Maneja la petición de registro controlando excepciones de negocio.
        """
        try:
            item = self._servicio.registrar_elemento(nombre, categoria, valor)
            print(f"\n[ÉXITO Willys_IA]: Elemento #{item.id} '{item.nombre}' registrado correctamente.")
            return item
        except ValueError as err:
            print(f"\n[ALERTA DE NEGOCIO Willys_IA]: {err}")
            return None

    def listar(self, filtro_estado: Optional[str] = None) -> List[Willys_IA_ItemModel]:
        """
        Willys_IA: Retorna la lista de elementos y la despliega en consola.
        """
        return self._servicio.listar_elementos(filtro_estado)

    def actualizar_estado(self, id_elemento: int, nuevo_estado: str) -> bool:
        """
        Willys_IA: Maneja el cambio de estado de un registro.
        """
        try:
            ok = self._servicio.cambiar_estado(id_elemento, nuevo_estado)
            if ok:
                print(f"\n[ÉXITO Willys_IA]: Elemento #{id_elemento} actualizado a '{nuevo_estado.upper()}'.")
            return ok
        except ValueError as err:
            print(f"\n[ALERTA DE NEGOCIO Willys_IA]: {err}")
            return False

    def obtener_resumen_metricas(self) -> Dict[str, Any]:
        """
        Willys_IA: Calcula y retorna el resumen cuantitativo en formato dict.
        """
        return {
            "total_acumulado": self._servicio.calcular_total_valores(),
            "distribucion_estados": self._servicio.obtener_resumen_metricas(),
            "total_registros": len(self._servicio.listar_elementos())
        }

    def mostrar_resumen_metricas(self) -> None:
        """
        Willys_IA: Despliega el resumen cuantitativo en consola.
        """
        metricas = self.obtener_resumen_metricas()
        print("\n--- RESUMEN Y MÉTRICAS DEL SISTEMA ---")
        print(f"• Total acumulado de valores/unidades: {metricas['total_acumulado']:.2f}")
        print(f"• Distribución de registros por estado: {metricas['distribucion_estados']}")


# ============================================================================
# ENDPOINTS REST CON FLASK BLUEPRINT (Willys_IA)
# Equivalente en Spring Boot a un @RestController en /api/mvp
# ============================================================================

bp_mvp = Blueprint("mvp", __name__, url_prefix="/api/mvp")
controlador_mvp_singleton = Willys_IA_ItemController()


@bp_mvp.route("", methods=["GET"])
def api_listar_elementos() -> Response:
    """
    /** Endpoint GET: Lista todos los elementos del MVP. */
    Willys_IA: Retorna la colección en formato JSON con código HTTP 200.
    """
    estado = request.args.get("estado")
    items = controlador_mvp_singleton.listar(filtro_estado=estado)
    return jsonify([it.to_dict() for it in items]), 200


@bp_mvp.route("", methods=["POST"])
def api_registrar_elemento() -> Response:
    """
    /** Endpoint POST: Registra un nuevo elemento en el MVP. */
    Willys_IA: Valida las reglas de negocio en el Service y responde 201 o 400.
    """
    datos = request.get_json(silent=True) or request.form.to_dict()
    if not datos:
        return jsonify({"error": "Debe enviar un payload JSON o formulario válido."}), 400

    nombre = datos.get("nombre", "")
    categoria = datos.get("categoria", "General")
    try:
        valor = float(datos.get("valor", 0.0))
    except (ValueError, TypeError):
        return jsonify({"error": "El campo 'valor' debe ser un número válido."}), 400

    try:
        nuevo_item = controlador_mvp_singleton.servicio.registrar_elemento(
            nombre=nombre,
            categoria=categoria,
            valor=valor
        )
        return jsonify(nuevo_item.to_dict()), 201
    except ValueError as err:
        return jsonify({"error": str(err)}), 400


@bp_mvp.route("/<int:id_elemento>/estado", methods=["POST", "PUT"])
def api_actualizar_estado(id_elemento: int) -> Response:
    """
    /** Endpoint POST/PUT: Actualiza el estado de un elemento del MVP. */
    Willys_IA: Aplica transición de estado y responde con confirmación.
    """
    datos = request.get_json(silent=True) or request.form.to_dict()
    nuevo_estado = (datos.get("estado") if datos else None) or request.args.get("estado")

    if not nuevo_estado:
        return jsonify({"error": "Debe especificar el campo 'estado'."}), 400

    try:
        ok = controlador_mvp_singleton.servicio.cambiar_estado(id_elemento, nuevo_estado)
        return jsonify({
            "mensaje": f"Elemento #{id_elemento} actualizado a '{nuevo_estado.upper()}'.",
            "id": id_elemento,
            "nuevo_estado": nuevo_estado.upper(),
            "exito": ok
        }), 200
    except ValueError as err:
        return jsonify({"error": str(err)}), 400


@bp_mvp.route("/metricas", methods=["GET"])
def api_obtener_metricas() -> Response:
    """
    /** Endpoint GET: Retorna las métricas y KPIs cuantitativos en tiempo real. */
    Willys_IA: Retorna métricas del MVP.
    """
    return jsonify(controlador_mvp_singleton.obtener_resumen_metricas()), 200
