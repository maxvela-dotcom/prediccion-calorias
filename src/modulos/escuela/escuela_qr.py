# -*- coding: utf-8 -*-
"""
Generación de códigos QR (Willys_IA).
Usa `segno`, una dependencia pura de Python, para no requerir servicios externos.
"""

import io

import segno


def generar_qr_svg(texto: str, escala: int = 6) -> bytes:
    """Devuelve el QR como SVG listo para servir por HTTP."""
    qr = segno.make((texto or "").strip(), error="m")
    buffer = io.BytesIO()
    qr.save(
        buffer,
        kind="svg",
        scale=escala,
        border=2,
        dark="#0f172a",
        light="#ffffff",
    )
    return buffer.getvalue()
