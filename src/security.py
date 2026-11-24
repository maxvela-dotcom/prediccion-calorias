# -*- coding: utf-8 -*-
"""
Utilidades de seguridad del MVP (Willys_IA):
- Rate limiting con backend pluggable (memoria por defecto, Redis opcional).
- Validación CSRF para formularios y APIs JSON con sesión.
- Generación de tokens de un solo uso (verificación/recuperación).

Configuración por variables de entorno:
- RATE_LIMIT_BACKEND: "auto" (por defecto), "memory" o "redis".
- REDIS_URL: requerido para el backend Redis (ej. redis://127.0.0.1:6379/0).
Si Redis no está disponible, se usa memoria como fallback seguro.
"""

import os
import secrets
import time
from typing import Dict, List, Optional, Tuple
from flask import request, session


# ----------------------------------------------------------------------
# Backends de rate limiting
# ----------------------------------------------------------------------

class _MemoryRateLimitBackend:
    """Ventana deslizante en memoria: clave -> lista de timestamps."""

    nombre = "memory"

    def __init__(self) -> None:
        self._buckets: Dict[str, List[float]] = {}

    def permitir(self, key: str, max_attempts: int, window_seconds: int) -> bool:
        now = time.time()
        bucket = self._buckets.setdefault(key, [])
        bucket[:] = [t for t in bucket if now - t < window_seconds]
        if len(bucket) >= max_attempts:
            return False
        bucket.append(now)
        return True

    def limpiar(self) -> None:
        self._buckets.clear()


class _RedisRateLimitBackend:
    """
    Ventana deslizante en Redis mediante sorted sets y script Lua atómico.
    Si Redis falla, delega en memoria para no tumbar la aplicación.
    """

    nombre = "redis"
    _LUA = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local max = tonumber(ARGV[3])
    local member = ARGV[4]
    redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
    local used = redis.call('ZCARD', key)
    if used >= max then
        return 0
    end
    redis.call('ZADD', key, now, member)
    redis.call('EXPIRE', key, window)
    return 1
    """

    def __init__(self, url: str) -> None:
        import redis  # importación diferida: dependencia opcional

        self._client = redis.Redis.from_url(
            url, socket_connect_timeout=1, socket_timeout=1, decode_responses=True
        )
        self._fallback = _MemoryRateLimitBackend()
        self._aviso_emitido = False

    def _avisar_fallback(self, error: Exception) -> None:
        if not self._aviso_emitido:
            print(
                f"\n[ALERTA Willys_IA]: Redis no disponible ({error}). "
                "Rate limiting en memoria como fallback.\n"
            )
            self._aviso_emitido = True

    def permitir(self, key: str, max_attempts: int, window_seconds: int) -> bool:
        try:
            member = f"{time.time()}:{secrets.token_hex(4)}"
            permitido = self._client.eval(
                self._LUA,
                1,
                f"ratelimit:{key}",
                time.time(),
                window_seconds,
                max_attempts,
                member,
            )
            return bool(int(permitido))
        except Exception as err:  # noqa: BLE001 - fallback deliberado
            self._avisar_fallback(err)
            return self._fallback.permitir(key, max_attempts, window_seconds)

    def limpiar(self) -> None:
        self._fallback.limpiar()
        try:
            claves = list(self._client.scan_iter(match="ratelimit:*", count=500))
            if claves:
                self._client.delete(*claves)
        except Exception as err:  # noqa: BLE001 - no debe romper pruebas/limpieza
            self._avisar_fallback(err)


def _crear_backend() -> object:
    """Selecciona el backend según RATE_LIMIT_BACKEND / REDIS_URL."""
    eleccion = (os.environ.get("RATE_LIMIT_BACKEND") or "auto").strip().lower()
    redis_url = (os.environ.get("REDIS_URL") or "").strip()

    if eleccion == "memory":
        return _MemoryRateLimitBackend()

    if eleccion in ("auto", "redis") and redis_url:
        try:
            return _RedisRateLimitBackend(redis_url)
        except Exception as err:  # noqa: BLE001 - Redis es opcional
            print(
                f"\n[ALERTA Willys_IA]: no se pudo iniciar Redis ({err}). "
                "Rate limiting en memoria como fallback.\n"
            )

    if eleccion == "redis" and not redis_url:
        print(
            "\n[ALERTA Willys_IA]: RATE_LIMIT_BACKEND=redis sin REDIS_URL. "
            "Rate limiting en memoria como fallback.\n"
        )

    return _MemoryRateLimitBackend()


_BACKEND = _crear_backend()


def reconfigurar_backend(nombre: Optional[str] = None) -> None:
    """
    Recrea el backend de rate limiting (útil en pruebas o al cambiar env).
    `nombre` puede ser "memory", "redis" o "auto"; None respeta el entorno.
    """
    global _BACKEND
    anterior = os.environ.get("RATE_LIMIT_BACKEND")
    if nombre is not None:
        os.environ["RATE_LIMIT_BACKEND"] = nombre
    try:
        _BACKEND = _crear_backend()
    finally:
        if nombre is not None:
            if anterior is None:
                os.environ.pop("RATE_LIMIT_BACKEND", None)
            else:
                os.environ["RATE_LIMIT_BACKEND"] = anterior


def backend_actual() -> str:
    """Nombre del backend activo ("memory" o "redis")."""
    return getattr(_BACKEND, "nombre", "memory")


# ----------------------------------------------------------------------
# API de rate limiting
# ----------------------------------------------------------------------

def client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "local"


def rate_limit(key: str, max_attempts: int, window_seconds: int) -> bool:
    """Retorna True si la solicitud está permitida; False si excede el límite."""
    return _BACKEND.permitir(key, max_attempts, window_seconds)


def reset_rate_limits() -> None:
    """Limpia los contadores del backend activo (útil en pruebas)."""
    _BACKEND.limpiar()


# ----------------------------------------------------------------------
# CSRF y tokens
# ----------------------------------------------------------------------

def obtener_csrf_token() -> str:
    """Obtiene o crea el token CSRF asociado a la sesión actual."""
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validar_csrf() -> bool:
    """Compara el token de sesión con el token enviado (form o header X-CSRF-Token)."""
    token_sesion = session.get("_csrf_token")
    token_enviado = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    return bool(token_sesion and token_enviado and secrets.compare_digest(token_sesion, token_enviado))


def exigir_csrf_json() -> Optional[Tuple[dict, int]]:
    """
    Para endpoints JSON que usan sesión: exige header X-CSRF-Token.
    Si no hay sesión retorna None (la autenticación se valida aparte).
    """
    if not session.get("usuario_id"):
        return None
    if not validar_csrf():
        return {"error": "Token CSRF inválido o ausente."}, 403
    return None


def generar_token() -> str:
    return secrets.token_urlsafe(32)
