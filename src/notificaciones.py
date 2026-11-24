# -*- coding: utf-8 -*-
"""
Notificaciones por correo (Willys_IA).

Comportamiento:
- Si las variables SMTP están configuradas, intenta enviar el correo real.
- Si no están configuradas, o el envío falla, imprime el mensaje en consola
  (modo simulación local). Nunca interrumpe el flujo de registro/recuperación.

Variables de entorno:
- SMTP_HOST, SMTP_PORT (587 por defecto), SMTP_USER, SMTP_PASS
- SMTP_FROM (opcional; por defecto SMTP_USER)
- SMTP_USE_TLS (por defecto "true"; usar "false" para servidores sin STARTTLS)

[POR DEFINIR: proveedor SMTP institucional, credenciales y plantillas oficiales]
"""

import os
import smtplib
from email.message import EmailMessage
from typing import Dict, Optional

_MARCA_CONSOLA = "[CORREO - SIMULACIÓN LOCAL]"
_PLACEHOLDERS = (
    "tu_correo",
    "tu_contraseña",
    "tu_contrasena",
    "tu_password",
    "cambia-esta",
    "example.com",
)


def _es_placeholder(valor: str) -> bool:
    texto = (valor or "").strip().lower()
    return any(p in texto for p in _PLACEHOLDERS)


def smtp_configurado() -> bool:
    """Indica si hay credenciales reales (no placeholders) para enviar por SMTP."""
    host = os.environ.get("SMTP_HOST", "")
    usuario = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")
    if not (host and usuario and password):
        return False
    return not any(_es_placeholder(v) for v in (host, usuario, password))


def _imprimir_en_consola(destinatario: str, asunto: str, cuerpo: str) -> None:
    print(f"\n{_MARCA_CONSOLA}")
    print(f"  Para:    {destinatario}")
    print(f"  Asunto:  {asunto}")
    for linea in cuerpo.splitlines():
        print(f"  {linea}")
    print()


def enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> Dict[str, object]:
    """
    Envía un correo o cae a consola. Retorna el canal usado y el resultado.

    Contrato de retorno:
    {"canal": "smtp" | "consola", "enviado": bool, "motivo": str (opcional)}
    """
    if not smtp_configurado():
        _imprimir_en_consola(destinatario, asunto, cuerpo)
        return {"canal": "consola", "enviado": False, "motivo": "SMTP no configurado"}

    host = os.environ.get("SMTP_HOST", "")
    try:
        puerto = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError:
        puerto = 587
    usuario = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")
    remitente = os.environ.get("SMTP_FROM") or usuario
    usar_tls = (os.environ.get("SMTP_USE_TLS", "true").strip().lower() not in {"0", "false", "no"})

    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = remitente
    mensaje["To"] = destinatario
    mensaje.set_content(cuerpo)

    try:
        with smtplib.SMTP(host, puerto, timeout=10) as servidor:
            if usar_tls:
                servidor.starttls()
            if usuario:
                servidor.login(usuario, password)
            servidor.send_message(mensaje)
        print(f"\n[Correo enviado por SMTP a {destinatario}]\n")
        return {"canal": "smtp", "enviado": True}
    except Exception as err:  # noqa: BLE001 - el correo no debe tumbar la app
        print(
            f"\n[ALERTA Willys_IA]: no se pudo enviar el correo por SMTP ({err}). "
            "Se muestra el contenido en consola.\n"
        )
        _imprimir_en_consola(destinatario, asunto, cuerpo)
        return {"canal": "consola", "enviado": False, "motivo": str(err)}


def notificar_verificacion(destinatario: str, enlace: str) -> Dict[str, object]:
    """Notifica el enlace de verificación de correo (24 h)."""
    asunto = "Verifica tu correo - Predicción de Calorías UAB"
    cuerpo = (
        "Hola,\n\n"
        "Gracias por registrarte en la plataforma de Predicción de Calorías.\n"
        f"Verifica tu correo abriendo este enlace:\n{enlace}\n\n"
        "El enlace expira en 24 horas. Si no creaste la cuenta, ignora este mensaje."
    )
    return enviar_correo(destinatario, asunto, cuerpo)


def notificar_recuperacion(destinatario: str, enlace: str) -> Dict[str, object]:
    """Notifica el enlace de recuperación de contraseña (60 min)."""
    asunto = "Recupera tu contraseña - Predicción de Calorías UAB"
    cuerpo = (
        "Hola,\n\n"
        "Recibimos una solicitud para restablecer tu contraseña.\n"
        f"Abre este enlace para continuar:\n{enlace}\n\n"
        "El enlace expira en 60 minutos y solo puede usarse una vez. "
        "Si no solicitaste el cambio, ignora este mensaje."
    )
    return enviar_correo(destinatario, asunto, cuerpo)
