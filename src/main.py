# -*- coding: utf-8 -*-
"""
Punto de Entrada del Servidor Web Flask (Application Layer).
Willys_IA: Arquitectura Monolito Modular en Capas.
Proyecto: Predicción de calorías quemadas en una rutina con autenticación de usuarios.
"""

import sys
import os
import ipaddress
import logging
import socket
import time
from functools import wraps
from threading import Event, Thread
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

# Asegurar que la raíz de src esté en el sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Willys_IA: la consola de Windows puede usar cp1252 y romper al imprimir emojis.
# Forzar UTF-8 con reemplazo evita que el servidor muera al arrancar.
for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(
            encoding="utf-8", errors="replace", line_buffering=True
        )
    except (AttributeError, OSError):
        pass

# Cargar variables de entorno locales antes de inicializar seguridad/BD.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # la dependencia es opcional en entornos mínimos
    pass

from database import init_db, respaldo_automatico
from security import obtener_csrf_token, validar_csrf, exigir_csrf_json, rate_limit, client_ip
from notificaciones import notificar_recuperacion, notificar_verificacion
from modulos.gestion_mvp.mvp_controller import bp_mvp, controlador_mvp_singleton
from modulos.usuarios.usuario_controller import bp_usuarios, controlador_usuarios_singleton
from modulos.usuarios import google_auth
from modulos.prediccion_calorias.caloria_controller import bp_calorias
from modulos.prediccion_calorias.met_catalogo import listar_actividades, metadatos_catalogo
from modulos.escuela.escuela_controller import bp_escuela, servicio_escuela_singleton

# Límites de intentos (el backend de almacenamiento es pluggable: memoria/Redis)
LIMITE_LOGIN = 10
VENTANA_LOGIN = 300
LIMITE_GOOGLE = 10
VENTANA_GOOGLE = 300
ESTADO_GOOGLE_VIDA = 600  # segundos
LIMITE_REGISTRO = 10
VENTANA_REGISTRO = 600
LIMITE_RECUPERACION = 5
VENTANA_RECUPERACION = 600
LIMITE_PERFIL = 30
VENTANA_PERFIL = 60


def _servicio_usuarios():
    return controlador_usuarios_singleton.servicio


def crear_app() -> Flask:
    """
    Willys_IA: Factoría de aplicación Flask (Application Factory Pattern).
    Configura rutas, sesión, SQLite, CSRF, rate limiting, blueprints y
    protección de la plataforma interna.
    """
    ruta_templates = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    app = Flask(__name__, template_folder=ruta_templates)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "uab-dev-secret-key")
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    init_db()

    app.register_blueprint(bp_mvp)
    app.register_blueprint(bp_usuarios)
    app.register_blueprint(bp_calorias)
    app.register_blueprint(bp_escuela)

    @app.context_processor
    def inject_csrf():
        return {
            "csrf_token": obtener_csrf_token(),
            "google_oauth": google_auth.estado(),
        }

    def login_requerido(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not session.get("usuario_id"):
                return redirect(url_for("login"))
            return view_func(*args, **kwargs)
        return wrapper

    def _abrir_sesion(usuario) -> None:
        session.clear()
        session["usuario_id"] = usuario.id
        session["usuario_nombre"] = usuario.nombre_completo
        session["usuario_email"] = usuario.email
        obtener_csrf_token()

    # ------------------------------------------------------------------
    # Rutas públicas
    # ------------------------------------------------------------------

    @app.route("/", methods=["GET"])
    def home():
        """Ruta pública: redirige a login o al dashboard según sesión."""
        if session.get("usuario_id"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/registro", methods=["GET", "POST"])
    def registro():
        """Crea una cuenta de usuario (registro) para acceder a la plataforma."""
        if request.method == "GET":
            if session.get("usuario_id"):
                return redirect(url_for("dashboard"))
            return render_template("register.html")

        if not validar_csrf():
            return render_template("register.html", error="Token CSRF inválido. Recarga la página e intenta de nuevo."), 400

        if not rate_limit(f"registro:{client_ip()}", LIMITE_REGISTRO, VENTANA_REGISTRO):
            return render_template("register.html", error="Demasiados registros desde esta conexión. Intenta más tarde."), 429

        nombre = (request.form.get("nombre") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        try:
            usuario = _servicio_usuarios().registrar_usuario(
                nombre=nombre,
                email=email,
                password=password,
                rol="ESTUDIANTE",
            )
            token = _servicio_usuarios().generar_verificacion(usuario.id)
            notificar_verificacion(
                usuario.email,
                url_for("verificar_email", token=token, _external=True),
            )
            _abrir_sesion(usuario)
            return redirect(url_for("dashboard"))
        except ValueError as err:
            return render_template("register.html", error=str(err)), 400

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """Inicio de sesión: solo usuarios autenticados acceden al dashboard interno."""
        if request.method == "GET":
            if session.get("usuario_id"):
                return redirect(url_for("dashboard"))
            return render_template("login.html")

        if not validar_csrf():
            return render_template("login.html", error="Token CSRF inválido. Recarga la página e intenta de nuevo."), 400

        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not rate_limit(f"login:{client_ip()}:{email}", LIMITE_LOGIN, VENTANA_LOGIN):
            return render_template("login.html", error="Demasiados intentos. Espera unos minutos e intenta de nuevo."), 429

        try:
            usuario = _servicio_usuarios().autenticar(email, password)
            _abrir_sesion(usuario)
            return redirect(url_for("dashboard"))
        except ValueError as err:
            return render_template("login.html", error=str(err)), 401

    @app.route("/logout", methods=["GET"])
    def logout():
        """Cierra la sesión del usuario."""
        session.clear()
        return redirect(url_for("login"))

    # ------------------------------------------------------------------
    # Google Sign-In (opcional; se activa con credenciales de Google Cloud)
    # ------------------------------------------------------------------

    def _google_mensaje(titulo: str, mensaje: str, estado: int = 200):
        return render_template(
            "mensaje.html",
            titulo=titulo,
            mensaje=mensaje,
            enlace_url=url_for("login"),
            enlace_texto="Volver al inicio de sesión",
        ), estado

    @app.route("/google/login", methods=["GET"])
    def google_login():
        """Envía al usuario a Google para que autorice su cuenta."""
        if not rate_limit(f"google_login:{client_ip()}", LIMITE_GOOGLE, VENTANA_GOOGLE):
            return _google_mensaje(
                "Demasiadas solicitudes",
                "Espera unos minutos antes de intentar entrar con Google.",
                429,
            )
        if not google_auth.configurado():
            return _google_mensaje("Google Sign-In pendiente", google_auth.MENSAJE_PENDIENTE)

        uri = google_auth.redirect_uri() or request.host_url.rstrip("/") + "/google/callback"
        state = google_auth.nuevo_state()
        session["google_oauth_state"] = {"valor": state, "ts": time.time()}
        session["google_oauth_redirect"] = uri
        try:
            destino = google_auth.url_autorizacion(state, uri)
        except ValueError as err:
            return _google_mensaje("No se pudo iniciar con Google", str(err), 400)
        return redirect(destino)

    @app.route("/google/callback", methods=["GET"])
    def google_callback():
        """Valida el `state`, verifica el ID token y abre la sesión local."""
        if not rate_limit(f"google_callback:{client_ip()}", LIMITE_GOOGLE, VENTANA_GOOGLE):
            return _google_mensaje(
                "Demasiadas solicitudes",
                "Espera unos minutos antes de intentar entrar con Google.",
                429,
            )
        if not google_auth.configurado():
            return _google_mensaje("Google Sign-In pendiente", google_auth.MENSAJE_PENDIENTE)

        guardado = session.pop("google_oauth_state", None)
        uri = session.pop("google_oauth_redirect", "") or (
            google_auth.redirect_uri() or request.host_url.rstrip("/") + "/google/callback"
        )

        if request.args.get("error"):
            return _google_mensaje(
                "Acceso cancelado",
                "Google no pudo completar la autorización. Intenta nuevamente.",
                400,
            )
        if (
            not guardado
            or time.time() - float(guardado.get("ts", 0)) > ESTADO_GOOGLE_VIDA
            or not google_auth.state_valido(request.args.get("state"), guardado.get("valor"))
        ):
            return _google_mensaje(
                "Solicitud inválida",
                "El enlace de Google venció o no es válido. Vuelve a intentarlo.",
                400,
            )

        code = request.args.get("code") or ""
        try:
            claims = google_auth.intercambiar_y_verificar(code, uri)
            usuario = _servicio_usuarios().autenticar_google(claims)
        except RuntimeError as err:
            app.logger.error("Google callback: configuración incompleta: %s", err)
            return _google_mensaje("Configuración incompleta", str(err), 500)
        except ValueError as err:
            app.logger.warning("Google callback rechazado: %s", err)
            return _google_mensaje("No se pudo entrar con Google", str(err), 401)
        except Exception:
            # Nunca dejar el 500 genérico: queda registrado en data/servidor.log.
            app.logger.exception("Error inesperado en /google/callback")
            return _google_mensaje(
                "No se pudo entrar con Google",
                "Ocurrió un error interno al completar el inicio de sesión. "
                "Revisa data/servidor.log e inténtalo de nuevo.",
                500,
            )

        _abrir_sesion(usuario)
        return redirect(url_for("dashboard"))

    @app.route("/verificar/<token>", methods=["GET"])
    def verificar_email(token: str):
        """Verifica el correo con un token de un solo uso."""
        try:
            usuario = _servicio_usuarios().verificar_email(token)
            return render_template(
                "mensaje.html",
                titulo="Correo verificado",
                mensaje=f"El correo {usuario.email} fue verificado correctamente.",
                enlace_url=url_for("dashboard") if session.get("usuario_id") else url_for("login"),
                enlace_texto="Ir a la plataforma" if session.get("usuario_id") else "Iniciar sesión",
            ), 200
        except ValueError as err:
            return render_template(
                "mensaje.html",
                titulo="No se pudo verificar",
                mensaje=str(err),
                enlace_url=url_for("login"),
                enlace_texto="Volver al inicio de sesión",
            ), 400

    @app.route("/recuperar", methods=["GET", "POST"])
    def recuperar_password():
        """Solicita un enlace de recuperación (SMTP opcional o consola local)."""
        if request.method == "GET":
            return render_template("recuperar.html")

        if not validar_csrf():
            return render_template("recuperar.html", error="Token CSRF inválido. Recarga la página e intenta de nuevo."), 400

        if not rate_limit(f"recuperar:{client_ip()}", LIMITE_RECUPERACION, VENTANA_RECUPERACION):
            return render_template("recuperar.html", error="Demasiadas solicitudes. Intenta más tarde."), 429

        email = (request.form.get("email") or "").strip().lower()
        token = _servicio_usuarios().solicitar_reset(email)
        if token:
            notificar_recuperacion(
                email,
                url_for("reset_password", token=token, _external=True),
            )

        # Respuesta genérica: no revela si el correo existe.
        return render_template(
            "recuperar.html",
            mensaje="Si el correo está registrado, se generó un enlace de recuperación. Revisa tu bandeja de entrada o la consola del servidor (modo local).",
        ), 200

    @app.route("/reset/<token>", methods=["GET", "POST"])
    def reset_password(token: str):
        """Restablece la contraseña usando un token de un solo uso."""
        if not _servicio_usuarios().token_reset_valido(token):
            return render_template(
                "mensaje.html",
                titulo="Enlace inválido",
                mensaje="El enlace de recuperación es inválido o expiró. Solicita uno nuevo.",
                enlace_url=url_for("recuperar_password"),
                enlace_texto="Solicitar otro enlace",
            ), 400

        if request.method == "GET":
            return render_template("reset.html", token=token)

        if not validar_csrf():
            return render_template("reset.html", token=token, error="Token CSRF inválido. Recarga la página e intenta de nuevo."), 400

        password = request.form.get("password") or ""
        confirmacion = request.form.get("password_confirm") or ""
        if password != confirmacion:
            return render_template("reset.html", token=token, error="Las contraseñas no coinciden."), 400

        try:
            _servicio_usuarios().restablecer_password(token, password)
            return render_template(
                "mensaje.html",
                titulo="Contraseña actualizada",
                mensaje="Tu contraseña fue actualizada. Ya puedes iniciar sesión.",
                enlace_url=url_for("login"),
                enlace_texto="Iniciar sesión",
            ), 200
        except ValueError as err:
            return render_template("reset.html", token=token, error=str(err)), 400

    # ------------------------------------------------------------------
    # Plataforma interna
    # ------------------------------------------------------------------

    @app.route("/dashboard", methods=["GET"])
    @login_requerido
    def dashboard():
        """Plataforma interna: visible solo después de iniciar sesión."""
        usuario = _servicio_usuarios().buscar_por_id(session["usuario_id"])
        if not usuario:
            session.clear()
            return redirect(url_for("login"))
        return render_template(
            "dashboard.html",
            usuario=usuario,
            actividades_met=listar_actividades(),
            catalogo_met=metadatos_catalogo(),
        )

    # ------------------------------------------------------------------
    # API de perfil, catálogo y CSRF
    # ------------------------------------------------------------------

    @app.route("/api/csrf-token", methods=["GET"])
    def api_csrf_token():
        """Expone el token CSRF de la sesión para peticiones JSON del frontend."""
        return jsonify({"csrf_token": obtener_csrf_token()}), 200

    @app.route("/api/perfil", methods=["GET"])
    @login_requerido
    def api_perfil_get():
        usuario = _servicio_usuarios().buscar_por_id(session["usuario_id"])
        if not usuario:
            return jsonify({"error": "Usuario no encontrado."}), 404
        return jsonify({"usuario": usuario.to_dict()}), 200

    @app.route("/api/perfil", methods=["POST", "PUT"])
    @login_requerido
    def api_perfil_update():
        error_csrf = exigir_csrf_json()
        if error_csrf is not None:
            cuerpo, estado = error_csrf
            return jsonify(cuerpo), estado

        if not rate_limit(f"perfil:{session['usuario_id']}", LIMITE_PERFIL, VENTANA_PERFIL):
            return jsonify({"error": "Demasiadas solicitudes. Intenta nuevamente en un minuto."}), 429

        datos = request.get_json(silent=True) or {}
        campos = {
            clave: datos.get(clave)
            for clave in (
                "peso_preferido_kg", "altura_preferida_cm", "edad", "sexo", "fc_reposo"
            )
            if clave in datos
        }
        if not campos:
            return jsonify({"error": "No se enviaron campos de perfil válidos."}), 400

        try:
            usuario = _servicio_usuarios().actualizar_perfil(
                session["usuario_id"], campos=campos
            )
            return jsonify({"usuario": usuario.to_dict()}), 200
        except ValueError as err:
            return jsonify({"error": str(err)}), 400

    @app.route("/api/met-catalogo", methods=["GET"])
    def api_met_catalogo():
        return jsonify(
            {
                "catalogo": metadatos_catalogo(),
                "actividades": listar_actividades(),
            }
        ), 200

    return app


def precargar_datos_semilla():
    """
    Willys_IA: Precarga datos iniciales de demostración.
    Nota: los usuarios semilla requieren contraseña segura (>=8, letras y números).
    """
    if not _servicio_usuarios().listar_usuarios():
        try:
            ana = _servicio_usuarios().registrar_usuario(
                "Ana Morales", "ana.morales@uab.edu.bo", "demo1234a", "ESTUDIANTE",
                peso_preferido_kg=60.0, edad=21, sexo="F", fc_reposo=68.0,
            )
            carlos = _servicio_usuarios().registrar_usuario(
                "Prof. Carlos Dávila", "cdavila@uab.edu.bo", "demo1234a", "DOCENTE",
                peso_preferido_kg=75.0, edad=45, sexo="M", fc_reposo=64.0,
            )
            _servicio_usuarios().marcar_email_verificado(ana.id)
            _servicio_usuarios().marcar_email_verificado(carlos.id)
        except ValueError:
            pass

    if not controlador_mvp_singleton.listar():
        controlador_mvp_singleton.registrar("Rutina de cardio inicial", "Cardio", 300.0)


# Instancia accesible para tests y servidores WSGI (gunicorn: main:app).
app = crear_app()
application = app  # alias WSGI habitual en plataformas como Render


def _prioridad_ip(ip: str) -> tuple:
    """Ordena las IPs: primero las privadas típicas de casa/escuela."""
    if ip.startswith("192.168."):
        return (0, ip)
    if ip.startswith("10."):
        return (1, ip)
    if ip.startswith("172."):
        try:
            segundo = int(ip.split(".")[1])
        except (IndexError, ValueError):
            segundo = 0
        if 16 <= segundo <= 31:
            return (2, ip)
    return (3, ip)


def _ip_de_ruta() -> str:
    """IP del adaptador que Windows usaría para salir (la WiFi/cable activa).

    No envía paquetes: solo consulta la tabla de rutas, así que funciona
    incluso en una red sin Internet (hotspot o LAN aislada).
    """
    for destino in (("8.8.8.8", 80), ("1.1.1.1", 80)):
        sonda = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sonda.connect(destino)
            valor = sonda.getsockname()[0]
            if valor and not valor.startswith("0."):
                return valor
        except OSError:
            pass
        finally:
            sonda.close()
    return ""


def _ips_locales() -> list:
    """Todas las IPv4 utilizables de la PC, en cualquier adaptador.

    Se usan para el certificado HTTPS: así la app sirve igual en la WiFi de la
    escuela, en otra WiFi, en un hotspot o por cable. No depende del nombre de
    la red ni de que haya Internet.
    """
    encontradas = set()

    # 1) Todas las direcciones registradas para el nombre del equipo.
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            encontradas.add(info[4][0])
    except OSError:
        pass

    # 2) La IP de la ruta activa (la que realmente usan los celulares).
    ruta = _ip_de_ruta()
    if ruta:
        encontradas.add(ruta)

    utiles = []
    for valor in encontradas:
        try:
            direccion = ipaddress.ip_address(valor)
        except ValueError:
            continue
        if direccion.version != 4:
            continue
        if direccion.is_loopback or direccion.is_link_local or direccion.is_unspecified:
            continue
        utiles.append(str(direccion))

    return sorted(set(utiles), key=_prioridad_ip)


def _ip_en_lan() -> str:
    """Willys_IA: descubre la IP local para que otros dispositivos sepan dónde entrar."""
    ruta = _ip_de_ruta()
    if ruta:
        return ruta
    ips = _ips_locales()
    return ips[0] if ips else "IP-DE-LA-PC"


def _crear_servidor_https(app, puerto: int, certificados: dict):
    from werkzeug.serving import make_server

    return make_server(
        "0.0.0.0",
        puerto,
        app,
        threaded=True,
        ssl_context=(certificados["cert"], certificados["key"]),
    )


def _abrir_https(app, puerto: int, certificados: dict, intentos: int = 5):
    """Crea el servidor HTTPS y empieza a atenderlo en segundo plano."""
    ultimo_error = None
    for _ in range(max(1, intentos)):
        try:
            servidor = _crear_servidor_https(app, puerto, certificados)
        except OSError as err:  # el puerto puede tardar en liberarse
            ultimo_error = err
            time.sleep(1)
            continue
        Thread(target=servidor.serve_forever, daemon=True).start()
        return servidor
    raise ultimo_error if ultimo_error else RuntimeError("No se pudo abrir HTTPS")


def _vigilar_red(app, puerto_https: int, estado: dict, detener: Event) -> None:
    """Mantiene el certificado al día cuando la PC cambia de red.

    Al pasar de una WiFi a otra, Windows asigna otra IP. Sin esto, el
    certificado dejaría de coincidir y los celulares verían un aviso de
    seguridad. Aquí se regenera el certificado (la CA se conserva) y se
    reinicia HTTPS con la IP nueva.
    """
    from certificados import asegurar_certificados, hosts_cubiertos

    while not detener.wait(15):
        try:
            ips = _ips_locales()
            if not ips:
                continue

            cambio_red = not set(ips).issubset(hosts_cubiertos())
            sin_https = estado.get("servidor") is None
            if not cambio_red and not sin_https:
                continue

            certificados = asegurar_certificados(ips + ["localhost"])

            anterior = estado.get("servidor")
            if anterior is not None:
                try:
                    anterior.shutdown()
                except Exception:
                    pass
                try:
                    anterior.server_close()
                except Exception:
                    pass

            estado["servidor"] = _abrir_https(app, puerto_https, certificados)
            estado["ips"] = ips

            if cambio_red:
                print("\n🔄 Cambió la red: certificado HTTPS actualizado.")
                for direccion in ips:
                    print(f"   https://{direccion}:{puerto_https}/escuela")
                print("   (los celulares deben usar la IP nueva; la CA no cambia)\n")
            else:
                print(f"\n✅ HTTPS restablecido en el puerto {puerto_https}.\n")
        except Exception as err:
            print(f"⚠️  No se pudo actualizar el certificado tras el cambio de red: {err}")


def _configurar_log_archivo():
    """Guarda también los tracebacks en data/servidor.log (además de la consola)."""
    from logging.handlers import RotatingFileHandler

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta = os.path.join(raiz, "data", "servidor.log")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    manejador = RotatingFileHandler(
        ruta, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    manejador.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s"
        )
    )
    logging.getLogger().addHandler(manejador)
    logging.getLogger().setLevel(logging.INFO)
    return ruta


def main():
    """
    Willys_IA: sirve la app compartida en la red local (0.0.0.0).
    En local levanta HTTP (5000) y HTTPS (5443) a la vez; en la nube (Render)
    respeta PORT y sirve solo HTTP en 0.0.0.0:$PORT.
    """
    ruta_log = _configurar_log_archivo()
    from werkzeug.serving import make_server

    # Render.com y otros PaaS inyectan PORT. No se generan certificados ni se
    # vigila la LAN: la plataforma termina TLS y asigna el puerto.
    puerto_nube = os.environ.get("PORT")
    if puerto_nube:
        puerto = int(puerto_nube)
        print(f"☁️  Modo nube: PORT={puerto} -> 0.0.0.0:{puerto}")
        print(f"📝 Log del servidor: {ruta_log}")
        servidor = make_server("0.0.0.0", puerto, app, threaded=True)
        servidor.serve_forever()
        return

    from certificados import asegurar_certificados

    puerto_http = int(os.environ.get("ESCUELA_HTTP_PORT", "5000"))
    puerto_https = int(os.environ.get("ESCUELA_HTTPS_PORT", "5443"))

    ips = _ips_locales()
    ip = _ip_en_lan()
    otras_ips = [valor for valor in ips if valor != ip]

    url_http = f"http://{ip}:{puerto_http}"
    url_https = f"https://{ip}:{puerto_https}"

    # Willys_IA: un respaldo por día antes de empezar a atender dispositivos.
    respaldo_hoy = None
    try:
        respaldo_hoy = respaldo_automatico()
    except Exception as err:
        print(f"⚠️  No se pudo crear el respaldo automático: {err}")

    certificados = None
    try:
        # El certificado cubre TODAS las IPs de la PC, no solo la actual:
        # así funciona igual en cualquier WiFi, hotspot o cable.
        certificados = asegurar_certificados((ips or [ip]) + ["localhost"])
    except Exception as err:  # la app sigue funcionando por HTTP
        print(f"⚠️  No se pudieron generar los certificados HTTPS: {err}")

    estado_https = {"servidor": None, "ips": ips}
    servidor_https = None
    if certificados:
        try:
            servidor_https = _abrir_https(app, puerto_https, certificados)
            estado_https["servidor"] = servidor_https
        except Exception as err:
            servidor_https = None
            print(f"⚠️  No se pudo iniciar HTTPS en el puerto {puerto_https}: {err}")

    servidor_http = make_server("0.0.0.0", puerto_http, app, threaded=True)

    print("\n" + "=" * 70)
    print("   UNIVERSIDAD ADVENTISTA DE BOLIVIA (UAB) - INGENIERÍA")
    print("   Escuela de Fútbol · asistencias compartidas (Willys_IA)")
    print("=" * 70)
    print("\n🚀 Servidor compartido iniciado.")
    if servicio_escuela_singleton.hay_usuarios():
        print(f"👉 En esta PC:      http://127.0.0.1:{puerto_http}/escuela")
        print(f"👉 En WiFi/LAN:     {url_http}/escuela")
    else:
        print("🆕 La base está vacía: crea el administrador en el primer arranque.")
        print(f"👉 Configuración:   http://127.0.0.1:{puerto_http}/escuela/setup")
        print(f"👉 Desde el celular: {url_http}/escuela/setup")
    if otras_ips:
        print(f"   Otras IPs de esta PC: {', '.join(otras_ips)}")
    if servidor_https:
        print(f"🔒 HTTPS en LAN:    {url_https}/escuela   ← instala la PWA y usa la cámara")
        print(f"🔐 Certificado CA:  {url_https}/ca.crt   ← instálalo una vez en cada celular")
    else:
        print("⚠️  HTTPS no disponible: la cámara y la PWA pueden quedar bloqueadas.")
    print(f"\n💾 Respaldo:         {url_http}/escuela/respaldo (solo administrador)")
    print(f"📝 Log del servidor: {ruta_log}")
    if respaldo_hoy:
        print(f"🗂️  Respaldo del día: {respaldo_hoy}")
    print("📶 Funciona en cualquier WiFi, hotspot o cable: solo deben estar en la misma red.")
    print("   Si la PC cambia de red, el certificado HTTPS se actualiza solo (CA no cambia).")
    print(f"⚠️  Habilita los puertos {puerto_http} y {puerto_https} en el Firewall de Windows")
    print("   (una sola vez: doble clic en preparar_red.bat).")
    print("📌 Presiona CTRL + C en la terminal para detener el servidor.\n")
    print("Capas activas:")
    print("  • Controller (Flask Blueprints + rutas web + roles)")
    print("  • Service Layer (Reglas de Negocio y autenticación)")
    print("  • Repository Layer (Persistencia en SQLite: data/app.db)")
    print("  • Model Layer (Entidades tipadas)")
    print("=" * 70 + "\n")

    detener = Event()
    if certificados:
        Thread(
            target=_vigilar_red,
            args=(app, puerto_https, estado_https, detener),
            daemon=True,
        ).start()

    try:
        servidor_http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        detener.set()
        servidor_http.shutdown()
        if servidor_https:
            servidor_https.shutdown()
        print("\n🛑 Servidor detenido.")


if __name__ == "__main__":
    main()
