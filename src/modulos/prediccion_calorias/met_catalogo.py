# -*- coding: utf-8 -*-
"""
Catálogo de actividades y valores MET (Metabolic Equivalent of Task).
Willys_IA: Valores de referencia aproximados para estimación educativa.

Trazabilidad del catálogo:
- Versión interna y fecha de revisión del archivo.
- Fuente bibliográfica de referencia.
- Estado de validación explícito (referencia educativa, no tabla institucional).
[POR DEFINIR: validar y ajustar el catálogo con un profesional/tabla institucional específica]
"""

from typing import Dict, List, Optional

VERSION_CATALOGO = "1.0.0"
FUENTE_CATALOGO = "Compendium of Physical Activities (Ainsworth et al.), valores simplificados"
REVISION_CATALOGO = "2026-11-16"
ESTADO_VALIDACION = "referencia_educativa_pendiente_validacion_institucional"

# Catálogo base: clave interna -> {nombre, met, descripcion}
CATALOGO_MET: Dict[str, Dict[str, object]] = {
    "caminar_suave": {"nombre": "Caminar suave", "met": 3.3, "descripcion": "Caminata lenta (< 4 km/h)"},
    "caminar_moderado": {"nombre": "Caminar moderado", "met": 4.3, "descripcion": "Caminata a paso medio"},
    "caminar_rapido": {"nombre": "Caminar rápido", "met": 5.0, "descripcion": "Caminata vigorosa"},
    "trotar": {"nombre": "Trotar", "met": 7.0, "descripcion": "Trote ligero"},
    "correr": {"nombre": "Correr", "met": 9.8, "descripcion": "Carrera moderada"},
    "ciclismo_suave": {"nombre": "Ciclismo suave", "met": 5.8, "descripcion": "Ciclismo recreativo"},
    "ciclismo_moderado": {"nombre": "Ciclismo moderado", "met": 7.5, "descripcion": "Ciclismo a ritmo medio"},
    "natacion_moderada": {"nombre": "Natación moderada", "met": 6.0, "descripcion": "Nado continuo moderado"},
    "fuerza_pesas": {"nombre": "Fuerza / pesas", "met": 6.0, "descripcion": "Entrenamiento de fuerza general"},
    "hiit": {"nombre": "HIIT", "met": 8.0, "descripcion": "Intervalos de alta intensidad"},
    "baile": {"nombre": "Baile", "met": 5.0, "descripcion": "Baile aeróbico moderado"},
    "yoga": {"nombre": "Yoga", "met": 3.0, "descripcion": "Yoga suave/moderado"},
    "eliptica": {"nombre": "Elíptica", "met": 5.0, "descripcion": "Ejercicio en elíptica"},
    "saltar_cuerda": {"nombre": "Saltar cuerda", "met": 10.0, "descripcion": "Salto de cuerda a ritmo moderado"},
    "futbol_recreativo": {"nombre": "Fútbol recreativo", "met": 7.0, "descripcion": "Juego recreativo"},
}


def listar_actividades() -> List[Dict[str, object]]:
    """Retorna la lista de actividades para UI/API."""
    items = []
    for key, val in CATALOGO_MET.items():
        items.append({"key": key, **val})
    return sorted(items, key=lambda x: str(x["nombre"]))


def metadatos_catalogo() -> Dict[str, object]:
    """Metadatos de trazabilidad del catálogo (versión, fuente y revisión)."""
    return {
        "version": VERSION_CATALOGO,
        "fuente": FUENTE_CATALOGO,
        "revision": REVISION_CATALOGO,
        "estado_validacion": ESTADO_VALIDACION,
        "total_actividades": len(CATALOGO_MET),
        "rango_met": {"min": 0.5, "max": 20.0},
    }


def obtener_met(nombre_o_key: str) -> Optional[float]:
    """Busca el MET por clave o por nombre (coincidencia exacta o parcial simple)."""
    if not nombre_o_key:
        return None
    q = nombre_o_key.strip().lower()
    if q in CATALOGO_MET:
        return float(CATALOGO_MET[q]["met"])
    for key, val in CATALOGO_MET.items():
        nombre = str(val["nombre"]).strip().lower()
        if q == nombre or q == key or q in nombre:
            return float(val["met"])
    return None


def met_valido(met: float) -> bool:
    """Regla: MET debe ser > 0 y dentro de un rango razonable para actividades físicas."""
    try:
        m = float(met)
    except (TypeError, ValueError):
        return False
    return 0.5 <= m <= 20.0
