# -*- coding: utf-8 -*-
"""
Google Sign-In para Willys_IA (flujo de Authorization Code con ID token).

El botón se muestra en /login, pero solo se activa cuando existen:
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- GOOGLE_REDIRECT_URI (opcional; por defecto se deriva del host de la petición)

Sin esas variables el módulo queda desactivado y la interfaz muestra la nota
`[POR DEFINIR: ...]`. La verificación del ID token se hace en el servidor con
`google-auth`; esa dependencia se importa de forma diferida para que la app
siga funcionando sin ella mientras no se configure Google.
"""

import json
import os
import secrets
from typing import Callable, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

AUTORIZAR_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "openid email profile"
MENSAJE_PENDIENTE = (
    "[POR DEFINIR: crea un proyecto en Google Cloud, habilita Google Sign-In y "
    "configura GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET y GOOGLE_REDIRECT_URI]"
)


class ErrorGoogle(ValueError):
    """Fallo controlado al canjear el código o verificar la identidad."""


def _limpio(clave: str) -> str:
    return (os.environ.get(clave) or "").strip()


def client_id() -> str:
    return _limpio("GOOGLE_CLIENT_ID")


def client_secret() -> str:
    return _limpio("GOOGLE_CLIENT_SECRET")


def redirect_uri() -> str:
    return _limpio("GOOGLE_REDIRECT_URI")


def dominio_permitido() -> str:
    """Restricción opcional por dominio (`hd`). Vacía = cualquier cuenta."""
    return _limpio("GOOGLE_HD")


def configurado() -> bool:
    """True solo cuando hay credenciales suficientes para iniciar el flujo."""
    return bool(client_id() and client_secret())


def estado() -> Dict[str, object]:
    """Estado que se inyecta en las plantillas para dibujar el botón."""
    return {
        "configurado": configurado(),
        "client_id_configurado": bool(client_id()),
        "redirect_uri": redirect_uri(),
        "mensaje": "" if configurado() else MENSAJE_PENDIENTE,
    }


def nuevo_state() -> str:
    """Nonce OAuth para proteger el callback contra CSRF."""
    return secrets.token_urlsafe(32)


def state_valido(recibido: Optional[str], esperado: Optional[str]) -> bool:
    if not recibido or not esperado:
        return False
    return secrets.compare_digest(str(recibido), str(esperado))


def url_autorizacion(state: str, uri_redirect: str) -> str:
    """Construye la URL a la que se envía al usuario en /google/login."""
    if not configurado():
        raise ValueError(MENSAJE_PENDIENTE)
    if not uri_redirect:
        raise ValueError("Falta GOOGLE_REDIRECT_URI para Google Sign-In.")

    parametros = {
        "client_id": client_id(),
        "redirect_uri": uri_redirect,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    if dominio_permitido():
        parametros["hd"] = dominio_permitido()
    return AUTORIZAR_URL + "?" + urlencode(parametros)


def _intercambiar_codigo(code: str, uri_redirect: str) -> str:
    """Canjea el `code` por un `id_token` usando la librería estándar."""
    datos = urlencode(
        {
            "code": code,
            "client_id": client_id(),
            "client_secret": client_secret(),
            "redirect_uri": uri_redirect,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    peticion = Request(
        TOKEN_URL,
        data=datos,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(peticion, timeout=10) as respuesta:  # noqa: S310 - URL fija
            contenido = json.loads(respuesta.read().decode("utf-8"))
    except HTTPError as err:
        # Google devuelve un JSON con `error`/`error_description` (p. ej.
        # invalid_client, invalid_grant, redirect_uri_mismatch). Se muestra al
        # usuario para poder corregir la configuración sin exponer secretos.
        detalle = ""
        try:
            cuerpo = json.loads(err.read().decode("utf-8", errors="replace"))
            detalle = str(cuerpo.get("error_description") or cuerpo.get("error") or "")
        except (ValueError, UnicodeDecodeError):
            pass
        mensaje = "Google rechazó el código de autorización"
        if detalle:
            mensaje += ": " + detalle
        raise ErrorGoogle(mensaje) from err
    except URLError as err:
        raise ErrorGoogle(
            "No se pudo conectar con Google para validar el inicio de sesión. "
            "Revisa la conexión de red del servidor."
        ) from err
    id_token = contenido.get("id_token")
    if not id_token:
        raise ValueError("Google no devolvió un id_token válido.")
    return str(id_token)


def _verificar_id_token(id_token: str) -> Dict[str, object]:
    """Valida firma, audiencia, emisor, expiración y correo verificados."""
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
    except ImportError as err:  # pragma: no cover - dependencia opcional
        raise RuntimeError(
            "Falta google-auth. Instala las dependencias con "
            "`pip install -r requirements.txt` para habilitar Google Sign-In."
        ) from err

    try:
        claims = google_id_token.verify_oauth2_token(
            id_token, google_requests.Request(), client_id()
        )
    except Exception as err:
        # Incluye GoogleAuthError (firma/audencia/emisor) y errores de
        # transporte al descargar las claves públicas de Google.
        raise ErrorGoogle(
            "Google no pudo verificar la identidad de la cuenta: " + str(err)
        ) from err
    correo = str(claims.get("email") or "").strip().lower()
    sub = str(claims.get("sub") or "").strip()
    if not correo or "@" not in correo or "." not in correo:
        raise ValueError("La cuenta de Google no entregó un correo válido.")
    if not sub:
        raise ValueError("La cuenta de Google no entregó un identificador válido.")
    if not claims.get("email_verified"):
        raise ValueError("Google no confirmó el correo de la cuenta.")

    nombre = str(claims.get("name") or correo.split("@")[0]).strip()
    return {
        "sub": sub,
        "email": correo,
        "nombre": nombre,
        "email_verificado": True,
    }


def intercambiar_y_verificar(
    code: str,
    uri_redirect: str,
    verificador: Optional[Callable[[str], Dict[str, object]]] = None,
) -> Dict[str, object]:
    """
    Canjea el código y devuelve los claims normalizados.

    `verificador` permite inyectar un verificador falso en las pruebas sin
    depender de Internet ni de credenciales reales.
    """
    if not configurado():
        raise ValueError(MENSAJE_PENDIENTE)
    if not code:
        raise ValueError("Google no devolvió un código de autorización.")

    id_token = _intercambiar_codigo(code, uri_redirect)
    verificar = verificador or _verificar_id_token
    return verificar(id_token)
