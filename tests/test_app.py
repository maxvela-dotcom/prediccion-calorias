# -*- coding: utf-8 -*-
"""
Módulo de Pruebas Unitarias e Integración Automatizadas.
Willys_IA: Compatible con pytest y con el módulo nativo unittest de Python estándar.
Valida tanto la lógica de capas en aislamiento (Unit Tests)
como los endpoints web de Flask a través de test_client() (Integration Tests).
"""

import sys
import os
import io
import json
import csv
import sqlite3
import contextlib
import unittest
import tempfile
import re
from unittest import mock

# Permitir importación directa desde src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import database
import security
import notificaciones
from modulos.gestion_mvp.mvp_model import Willys_IA_ItemModel
from modulos.gestion_mvp.mvp_repository import Willys_IA_ItemRepository
from modulos.gestion_mvp.mvp_service import Willys_IA_ItemService
from modulos.gestion_mvp.mvp_controller import Willys_IA_ItemController

from modulos.usuarios.usuario_model import Willys_IA_UsuarioModel
from modulos.usuarios.usuario_repository import Willys_IA_UsuarioRepository
from modulos.usuarios.usuario_service import Willys_IA_UsuarioService
from modulos.usuarios.usuario_controller import Willys_IA_UsuarioController

from modulos.prediccion_calorias.caloria_model import Willys_IA_CaloriaModel
from modulos.prediccion_calorias.caloria_repository import Willys_IA_CaloriaRepository
from modulos.prediccion_calorias.caloria_service import Willys_IA_CaloriaService
from modulos.prediccion_calorias import met_catalogo
from modulos.prediccion_calorias import regresion_lineal
from modulos.prediccion_calorias.regresion_lineal import RegresionLineal
import numpy as np

import main as modulo_main
from main import crear_app


def _csrf_from_html(html: str) -> str:
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return m.group(1) if m else ""


def _csrf_from_meta(html: str) -> str:
    m = re.search(r'name="csrf-token"\s+content="([^"]+)"', html)
    return m.group(1) if m else ""


def _csrf_api(client) -> str:
    return client.get("/api/csrf-token").get_json()["csrf_token"]


# Filas linealmente independientes (rango 5 con la columna de unos) para pruebas exactas.
FILAS_EXACTAS = [
    (68, 172, 31, 25), (74, 168, 27, 40), (61, 155, 44, 15),
    (82, 181, 22, 55), (57, 160, 52, 30), (90, 176, 35, 60),
    (65, 165, 29, 20), (78, 185, 41, 45), (72, 158, 25, 35),
    (85, 178, 48, 50), (60, 170, 33, 10), (69, 162, 38, 65),
]


class TestWillysIAProyectoModular(unittest.TestCase):
    """
    Willys_IA: Suite de pruebas de aseguramiento de calidad (QA).
    Audita la arquitectura monolito modular: Model, Repository, Service y Flask Controllers.
    """

    def setUp(self):
        """Willys_IA: Inicializa DB temporal, instancias limpias y cliente Flask antes de cada test."""
        self._tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self._tmp.close()
        self.db_path = self._tmp.name
        database.configurar_db(self.db_path)
        database.init_db(self.db_path)
        # Aislar las pruebas de servicios externos (Redis/SMTP) configurados en .env.
        self._smtp_previos = {
            clave: os.environ.pop(clave, None)
            for clave in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS")
        }
        security.reconfigurar_backend("memory")
        security.reset_rate_limits()

        # Capas Módulo Gestión MVP en aislamiento
        self.repo = Willys_IA_ItemRepository(self.db_path)
        self.servicio = Willys_IA_ItemService(self.repo)
        self.controlador = Willys_IA_ItemController(self.servicio)

        # Capas Módulo Usuarios en aislamiento
        self.repo_usuarios = Willys_IA_UsuarioRepository(self.db_path)
        self.servicio_usuarios = Willys_IA_UsuarioService(self.repo_usuarios)
        self.controlador_usuarios = Willys_IA_UsuarioController(self.servicio_usuarios)

        # Cliente de pruebas de integración Flask
        self.app = crear_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        for clave, valor in getattr(self, "_smtp_previos", {}).items():
            os.environ.pop(clave, None)
            if valor is not None:
                os.environ[clave] = valor
        try:
            if os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except Exception:
            pass

    # ========================================================================
    # 1. PRUEBAS UNITARIAS DE GESTIÓN MVP (SERVICIOS Y REPOSITORIO)
    # ========================================================================

    def test_tc01_registro_exitoso_happy_path(self):
        """TC-01: Verifica el registro exitoso a través de Service y Repository."""
        item = self.servicio.registrar_elemento(
            nombre="Canasta Solidaria",
            categoria="Alimentos",
            valor=150.0
        )
        self.assertIsNotNone(item)
        self.assertEqual(item.id, 1)
        self.assertEqual(item.nombre, "Canasta Solidaria")
        self.assertEqual(item.estado, "ACTIVO")
        self.assertEqual(len(self.repo.obtener_todos()), 1)

    def test_tc02_validacion_nombre_vacio_rechazo(self):
        """TC-02: Verifica que el Service lance ValueError ante nombres menores a 3 caracteres."""
        with self.assertRaises(ValueError):
            self.servicio.registrar_elemento(nombre="", categoria="Test", valor=10.0)

        with self.assertRaises(ValueError):
            self.servicio.registrar_elemento(nombre="   ", categoria="Test", valor=10.0)

        with self.assertRaises(ValueError):
            self.servicio.registrar_elemento(nombre="Ab", categoria="Test", valor=10.0)

        self.assertEqual(len(self.repo.obtener_todos()), 0)

    def test_tc03_rechazo_valor_numerico_negativo(self):
        """TC-03: Verifica que las reglas de negocio impidan cantidades menores a cero."""
        with self.assertRaises(ValueError):
            self.servicio.registrar_elemento(
                nombre="Aporte Negativo",
                categoria="Finanzas",
                valor=-25.0
            )

    def test_tc04_prevencion_duplicados_activos(self):
        """TC-04: Verifica que el Service bloquee duplicados del mismo nombre activo."""
        self.servicio.registrar_elemento(nombre="Donación Escolar", categoria="Educación", valor=50.0)
        with self.assertRaises(ValueError):
            self.servicio.registrar_elemento(nombre="Donación Escolar", categoria="Educación", valor=50.0)

        self.assertEqual(len(self.repo.obtener_todos()), 1)

    def test_tc05_controlador_y_actualizacion_estado(self):
        """TC-05: Verifica que el Controller maneje defensivamente y actualice estados."""
        item = self.controlador.registrar("Tarea Proyecto", "Desarrollo", 40.0)
        self.assertIsNotNone(item)

        invalido = self.controlador.registrar("", "Error", 10.0)
        self.assertIsNone(invalido)

        ok = self.controlador.actualizar_estado(item.id, "ENTREGADO")
        self.assertTrue(ok)
        self.assertEqual(self.servicio.calcular_total_valores(), 40.0)

    # ========================================================================
    # 2. PRUEBAS UNITARIAS DE USUARIOS
    # ========================================================================

    def test_tc06_registro_usuario_exitoso(self):
        """TC-06: Verifica registro exitoso de usuario con rol, estado inicial y hash de contraseña."""
        usuario = self.servicio_usuarios.registrar_usuario(
            nombre="Samuel Quispe",
            email="squispe@uab.edu.bo",
            password="clave1234",
            rol="ESTUDIANTE"
        )
        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.id, 1)
        self.assertEqual(usuario.nombre_completo, "Samuel Quispe")
        self.assertEqual(usuario.email, "squispe@uab.edu.bo")
        self.assertEqual(usuario.rol, "ESTUDIANTE")
        self.assertEqual(usuario.estado, "ACTIVO")
        self.assertTrue(usuario.password_hash and usuario.password_hash != "clave1234")

    def test_tc07_validacion_usuario_invalido(self):
        """TC-07: Verifica rechazo de nombres cortos, correos inválidos o contraseña débil."""
        with self.assertRaises(ValueError):
            self.servicio_usuarios.registrar_usuario(nombre="Al", email="al@uab.edu.bo", password="clave1234")

        with self.assertRaises(ValueError):
            self.servicio_usuarios.registrar_usuario(nombre="Alvaro Torres", email="correoinvalido", password="clave1234")

        with self.assertRaises(ValueError):
            self.servicio_usuarios.registrar_usuario(nombre="Alvaro Torres", email="alvaro@uab.edu.bo", password="12345678")  # sin letras

    def test_tc08_prevencion_email_duplicado(self):
        """TC-08: Verifica que el Service impida registrar dos veces el mismo correo."""
        self.servicio_usuarios.registrar_usuario("Elena Ruiz", "elena@uab.edu.bo", "clave1234", "DOCENTE")
        with self.assertRaises(ValueError):
            self.servicio_usuarios.registrar_usuario("Elena Otra", "elena@uab.edu.bo", "clave1234", "ESTUDIANTE")

    def test_tc09_controlador_usuarios_defensivo(self):
        """TC-09: Verifica que el Controller maneje defensivamente errores y liste usuarios."""
        u = self.controlador_usuarios.registrar("María Rojas", "mrojas@uab.edu.bo", "clave1234", "VOLUNTARIO")
        self.assertIsNotNone(u)

        fallido = self.controlador_usuarios.registrar("", "bad_email", "12345678", "INVALID")
        self.assertIsNone(fallido)

    # ========================================================================
    # 3. PRUEBAS DE INTEGRACIÓN WEB FLASK (ENDPOINTS REST Y VISTAS)
    # ========================================================================

    def test_tc10_flask_home_redirige_a_login(self):
        """TC-10: Verifica que la ruta raíz '/' redirija al login cuando no hay sesión."""
        response = self.client.get("/", follow_redirects=False)
        self.assertIn(response.status_code, (302, 301))
        self.assertIn("/login", response.headers.get("Location", ""))

    def test_tc11_flask_api_mvp_registro_y_listado(self):
        """TC-11: Verifica que POST /api/mvp cree elementos y GET /api/mvp los retorne en JSON."""
        payload = {"nombre": "Kit Primeros Auxilios", "categoria": "Salud", "valor": 85.50}
        post_res = self.client.post("/api/mvp", json=payload)
        self.assertEqual(post_res.status_code, 201)
        data = post_res.get_json()
        self.assertEqual(data["nombre"], "Kit Primeros Auxilios")

        # Verificar listado
        get_res = self.client.get("/api/mvp")
        self.assertEqual(get_res.status_code, 200)
        items = get_res.get_json()
        self.assertTrue(any(it["nombre"] == "Kit Primeros Auxilios" for it in items))

    def test_tc12_flask_api_mvp_rechazo_datos_invalidos(self):
        """TC-12: Verifica que POST /api/mvp rechace datos inválidos con HTTP 400."""
        # Nombre menor a 3 caracteres
        payload = {"nombre": "X", "categoria": "Test", "valor": 10.0}
        res = self.client.post("/api/mvp", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.get_json())

    def test_tc13_flask_api_usuarios_registro_y_unicidad(self):
        """TC-13: Verifica registro de usuarios vía API y bloqueo de emails duplicados con HTTP 400."""
        user_data = {"nombre": "David Choque", "email": "dchoque@uab.edu.bo", "password": "clave1234", "rol": "ESTUDIANTE"}
        res1 = self.client.post("/api/usuarios", json=user_data)
        self.assertEqual(res1.status_code, 201)

        # Intento duplicado debe responder HTTP 400
        res2 = self.client.post("/api/usuarios", json=user_data)
        self.assertEqual(res2.status_code, 400)
        self.assertIn("Ya existe un usuario", res2.get_json()["error"])

    def test_tc14_flask_api_cambio_estado(self):
        """TC-14: Verifica actualización de estado de un elemento vía POST /api/mvp/<id>/estado."""
        crear_res = self.client.post("/api/mvp", json={"nombre": "Carpa Médica", "categoria": "Salud", "valor": 300.0})
        item_id = crear_res.get_json()["id"]

        update_res = self.client.post(f"/api/mvp/{item_id}/estado", json={"estado": "COMPLETADO"})
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.get_json()["nuevo_estado"], "COMPLETADO")

    # ========================================================================
    # 4. PRUEBAS DE PREDICCIÓN DE CALORÍAS Y AUTENTICACIÓN
    # ========================================================================

    def test_tc15_calorias_service_prediccion_valida(self):
        """TC-15: Verifica cálculo MET*peso*(min/60) y persistencia por usuario."""
        u = self.servicio_usuarios.registrar_usuario("Cal User", "cal@uab.edu.bo", "clave1234")
        repo_cal = Willys_IA_CaloriaRepository(self.db_path)
        servicio_cal = Willys_IA_CaloriaService(repo_cal)
        item = servicio_cal.predecir_y_guardar(u.id, "Trotar", 70.0, 60.0, 8.0)
        self.assertEqual(item.calorias_estimadas, 560.0)
        self.assertEqual(len(servicio_cal.listar_por_usuario(u.id)), 1)
        self.assertEqual(len(servicio_cal.listar_por_usuario(u.id + 1)), 0)

    def test_tc16_calorias_service_rechazo_datos_invalidos(self):
        """TC-16: Rechaza peso/duración fuera de rango, MET inválido y actividad corta."""
        u = self.servicio_usuarios.registrar_usuario("Cal User 2", "cal2@uab.edu.bo", "clave1234")
        servicio_cal = Willys_IA_CaloriaService(Willys_IA_CaloriaRepository(self.db_path))
        with self.assertRaises(ValueError):
            servicio_cal.predecir_y_guardar(u.id, "Trotar", 0, 30, 7)
        with self.assertRaises(ValueError):
            servicio_cal.predecir_y_guardar(u.id, "Trotar", 70, 0, 7)
        with self.assertRaises(ValueError):
            servicio_cal.predecir_y_guardar(u.id, "Zzz", 70, 30, 0)  # actividad sin catálogo
        with self.assertRaises(ValueError):
            servicio_cal.predecir_y_guardar(u.id, "ab", 70, 30, 7)
        with self.assertRaises(ValueError):
            servicio_cal.predecir_y_guardar(u.id, "Trotar", 501, 30, 7)
        with self.assertRaises(ValueError):
            servicio_cal.predecir_y_guardar(u.id, "Trotar", 70, 1441, 7)

    def test_tc17_api_calorias_requiere_autenticacion(self):
        """TC-17: GET/POST /api/calorias sin sesión responde 401."""
        get_res = self.client.get("/api/calorias")
        self.assertEqual(get_res.status_code, 401)
        post_res = self.client.post("/api/calorias", json={"tipo_actividad": "Correr", "peso_kg": 70, "duracion_min": 30, "met": 9.8})
        self.assertEqual(post_res.status_code, 401)

    def test_tc18_flujo_web_registro_login_dashboard_y_prediccion(self):
        """TC-18: Registro crea sesión y permite usar dashboard y API de calorías (con CSRF)."""
        c = self.client
        page = c.get("/registro")
        csrf = _csrf_from_html(page.get_data(as_text=True))
        r = c.post("/registro", data={"csrf_token": csrf, "nombre": "Test User", "email": "test.user@uab.edu.bo", "password": "clave1234"}, follow_redirects=False)
        self.assertIn(r.status_code, (302, 303))
        self.assertIn("/dashboard", r.headers.get("Location", ""))
        d = c.get("/dashboard")
        self.assertEqual(d.status_code, 200)
        self.assertIn(b"Plataforma de Predicci", d.data)
        csrf_api = _csrf_from_meta(d.get_data(as_text=True))
        self.assertTrue(csrf_api)
        p = c.post("/api/calorias", json={"tipo_actividad": "Correr", "peso_kg": 70, "duracion_min": 30, "met": 10},
                   headers={"X-CSRF-Token": csrf_api})
        self.assertEqual(p.status_code, 201)
        self.assertAlmostEqual(p.get_json()["calorias_estimadas"], 350.0, places=2)
        g = c.get("/api/calorias")
        self.assertEqual(g.status_code, 200)
        self.assertTrue(any(x["tipo_actividad"] == "Correr" for x in g.get_json()["items"]))
        c.get("/logout")
        d2 = c.get("/dashboard", follow_redirects=False)
        self.assertIn(d2.status_code, (302, 301))
        self.assertIn("/login", d2.headers.get("Location", ""))

    def test_tc19_login_invalido_y_csrf(self):
        """TC-19: Login con credenciales incorrectas falla y POST sin CSRF es rechazado."""
        c = self.client
        # registrar usuario vía API (sin CSRF, es JSON)
        c.post("/api/usuarios", json={"nombre": "User Dos", "email": "user2@uab.edu.bo", "password": "clave1234"})
        c.get("/logout")
        page = c.get("/login")
        csrf = _csrf_from_html(page.get_data(as_text=True))
        r_bad = c.post("/login", data={"csrf_token": csrf, "email": "user2@uab.edu.bo", "password": "mala1234"}, follow_redirects=False)
        self.assertEqual(r_bad.status_code, 401)
        # sin csrf
        r_csrf = c.post("/login", data={"email": "user2@uab.edu.bo", "password": "clave1234"}, follow_redirects=False)
        self.assertEqual(r_csrf.status_code, 400)

    def test_tc20_perfil_y_catalogo_met(self):
        """TC-20: API de perfil y catálogo MET disponibles; perfil actualiza peso preferido."""
        c = self.client
        page = c.get("/registro")
        csrf = _csrf_from_html(page.get_data(as_text=True))
        c.post("/registro", data={"csrf_token": csrf, "nombre": "Perfil User", "email": "perfil@uab.edu.bo", "password": "clave1234"})
        met = c.get("/api/met-catalogo")
        self.assertEqual(met.status_code, 200)
        acts = met.get_json()["actividades"]
        self.assertTrue(any(a["nombre"] == "Correr" for a in acts))
        csrf = _csrf_api(c)
        upd = c.post("/api/perfil", json={"peso_preferido_kg": 72.5}, headers={"X-CSRF-Token": csrf})
        self.assertEqual(upd.status_code, 200)
        self.assertEqual(upd.get_json()["usuario"]["peso_preferido_kg"], 72.5)

    # ========================================================================
    # 5. MODELO AMPLIADO, SEGURIDAD, CSV Y RECUPERACIÓN/VERIFICACIÓN
    # ========================================================================

    def test_tc21_calorias_keytel_y_fallback_met(self):
        """TC-21: Aplica la ecuación de Keytel con FC/edad/sexo y cae a MET si faltan datos."""
        u = self.servicio_usuarios.registrar_usuario("Keytel User", "keytel@uab.edu.bo", "clave1234")
        servicio = Willys_IA_CaloriaService(Willys_IA_CaloriaRepository(self.db_path))

        hombre = servicio.predecir_y_guardar(
            u.id, "Correr", 70.0, 30.0, 9.8, fc_promedio=150, edad=30, sexo="M"
        )
        esperado_m = round(((-55.0969 + 0.6309 * 150 + 0.1988 * 70 + 0.2017 * 30) / 4.184) * 30, 2)
        self.assertEqual(hombre.metodo_calculo, "KEYTEL")
        self.assertAlmostEqual(hombre.calorias_estimadas, esperado_m, places=2)

        mujer = servicio.predecir_y_guardar(
            u.id, "Trotar", 60.0, 45.0, 8.0, fc_promedio=140, edad=25, sexo="F"
        )
        esperado_f = round(((-20.4022 + 0.4472 * 140 - 0.1263 * 60 + 0.0740 * 25) / 4.184) * 45, 2)
        self.assertEqual(mujer.metodo_calculo, "KEYTEL")
        self.assertAlmostEqual(mujer.calorias_estimadas, esperado_f, places=2)

        sin_fc = servicio.predecir_y_guardar(u.id, "Yoga", 70.0, 60.0, 3.0, edad=30, sexo="M")
        self.assertEqual(sin_fc.metodo_calculo, "MET")
        self.assertAlmostEqual(sin_fc.calorias_estimadas, 210.0, places=2)

    def test_tc22_rate_limit_en_memoria(self):
        """TC-22: El rate limiting permite hasta el máximo y luego bloquea; reset limpia."""
        self.assertTrue(security.rate_limit("prueba:rl", 2, 60))
        self.assertTrue(security.rate_limit("prueba:rl", 2, 60))
        self.assertFalse(security.rate_limit("prueba:rl", 2, 60))
        security.reset_rate_limits()
        self.assertTrue(security.rate_limit("prueba:rl", 2, 60))

    def test_tc23_exportacion_csv_con_filtros(self):
        """TC-23: GET /api/calorias/export.csv requiere sesión y respeta los filtros."""
        self.assertEqual(self.client.get("/api/calorias/export.csv").status_code, 401)

        c = self.client
        page = c.get("/registro")
        csrf = _csrf_from_html(page.get_data(as_text=True))
        c.post("/registro", data={"csrf_token": csrf, "nombre": "Csv User", "email": "csv@uab.edu.bo", "password": "clave1234"})
        csrf_api = _csrf_api(c)
        c.post("/api/calorias", json={"tipo_actividad": "Correr", "peso_kg": 70, "duracion_min": 30, "met": 10},
               headers={"X-CSRF-Token": csrf_api})
        c.post("/api/calorias", json={"tipo_actividad": "Yoga", "peso_kg": 70, "duracion_min": 20, "met": 3},
               headers={"X-CSRF-Token": csrf_api})

        res = c.get("/api/calorias/export.csv")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.headers.get("Content-Type", ""))
        self.assertIn("attachment", res.headers.get("Content-Disposition", ""))
        texto = res.get_data(as_text=True)
        self.assertIn("Actividad", texto)
        self.assertIn("Correr", texto)
        self.assertIn("Yoga", texto)

        filtrado = c.get("/api/calorias/export.csv?q=yoga").get_data(as_text=True)
        self.assertIn("Yoga", filtrado)
        self.assertNotIn("Correr", filtrado)

    def test_tc24_verificacion_de_correo_un_solo_uso(self):
        """TC-24: El token de verificación marca el correo y no puede reutilizarse."""
        u = self.servicio_usuarios.registrar_usuario("Verifica User", "verifica@uab.edu.bo", "clave1234")
        self.assertEqual(u.email_verificado, 0)
        token = self.servicio_usuarios.generar_verificacion(u.id)
        verificado = self.servicio_usuarios.verificar_email(token)
        self.assertEqual(verificado.email_verificado, 1)
        self.assertIsNone(verificado.token_verificacion)
        with self.assertRaises(ValueError):
            self.servicio_usuarios.verificar_email(token)

    def test_tc25_recuperacion_de_password(self):
        """TC-25: El reset actualiza la contraseña, invalida el token y exige política segura."""
        self.servicio_usuarios.registrar_usuario("Reset User", "reset@uab.edu.bo", "clave1234")
        self.assertIsNone(self.servicio_usuarios.solicitar_reset("noexiste@uab.edu.bo"))

        token = self.servicio_usuarios.solicitar_reset("reset@uab.edu.bo")
        self.assertTrue(token)
        self.assertTrue(self.servicio_usuarios.token_reset_valido(token))

        with self.assertRaises(ValueError):
            self.servicio_usuarios.restablecer_password(token, "corta")

        self.servicio_usuarios.restablecer_password(token, "nueva1234")
        self.servicio_usuarios.autenticar("reset@uab.edu.bo", "nueva1234")
        with self.assertRaises(ValueError):
            self.servicio_usuarios.autenticar("reset@uab.edu.bo", "clave1234")
        with self.assertRaises(ValueError):
            self.servicio_usuarios.restablecer_password(token, "otra1234")

    def test_tc26_csrf_en_apis_json(self):
        """TC-26: POST /api/calorias y /api/perfil sin header CSRF responden 403."""
        c = self.client
        page = c.get("/registro")
        csrf = _csrf_from_html(page.get_data(as_text=True))
        c.post("/registro", data={"csrf_token": csrf, "nombre": "Csrf User", "email": "csrf@uab.edu.bo", "password": "clave1234"})
        csrf_api = _csrf_api(c)
        payload = {"tipo_actividad": "Correr", "peso_kg": 70, "duracion_min": 30, "met": 10}

        sin_header = c.post("/api/calorias", json=payload)
        self.assertEqual(sin_header.status_code, 403)
        sin_header_perfil = c.post("/api/perfil", json={"peso_preferido_kg": 70})
        self.assertEqual(sin_header_perfil.status_code, 403)
        con_header = c.post("/api/calorias", json=payload, headers={"X-CSRF-Token": csrf_api})
        self.assertEqual(con_header.status_code, 201)

    def test_tc27_perfil_ampliado_y_keytel_desde_dashboard(self):
        """TC-27: El perfil guarda edad/sexo/FC y la API usa Keytel con el perfil."""
        c = self.client
        page = c.get("/registro")
        csrf = _csrf_from_html(page.get_data(as_text=True))
        c.post("/registro", data={"csrf_token": csrf, "nombre": "Perfil Amplio", "email": "amplio@uab.edu.bo", "password": "clave1234"})
        csrf_api = _csrf_api(c)
        headers = {"X-CSRF-Token": csrf_api}

        upd = c.post("/api/perfil", json={
            "peso_preferido_kg": 70, "edad": 30, "sexo": "M", "fc_reposo": 60
        }, headers=headers)
        self.assertEqual(upd.status_code, 200)
        usuario = upd.get_json()["usuario"]
        self.assertEqual(usuario["edad"], 30)
        self.assertEqual(usuario["sexo"], "M")
        self.assertEqual(usuario["fc_reposo"], 60)

        pred = c.post("/api/calorias", json={
            "tipo_actividad": "Correr", "peso_kg": 70, "duracion_min": 30, "met": 9.8, "fc_promedio": 150
        }, headers=headers)
        self.assertEqual(pred.status_code, 201)
        self.assertEqual(pred.get_json()["metodo_calculo"], "KEYTEL")
        self.assertEqual(pred.get_json()["edad"], 30)

        invalido = c.post("/api/perfil", json={"edad": 5}, headers=headers)
        self.assertEqual(invalido.status_code, 400)

        dashboard = c.get("/dashboard").get_data(as_text=True)
        self.assertIn("No verificado", dashboard)
        self.assertIn("Keytel", dashboard)

    def test_tc28_api_usuarios_protegida_y_baja_con_csrf(self):
        """TC-28: Listar usuarios exige sesión; la baja exige sesión, CSRF y autorización."""
        self.assertEqual(self.client.get("/api/usuarios").status_code, 401)
        self.assertEqual(self.client.post("/api/usuarios/1/baja").status_code, 401)

        c = self.client
        page = c.get("/registro")
        csrf = _csrf_from_html(page.get_data(as_text=True))
        c.post("/registro", data={"csrf_token": csrf, "nombre": "Baja User", "email": "baja@uab.edu.bo", "password": "clave1234"})
        listado = c.get("/api/usuarios")
        self.assertEqual(listado.status_code, 200)
        usuario = next(u for u in listado.get_json() if u["email"] == "baja@uab.edu.bo")

        sin_csrf = c.post(f"/api/usuarios/{usuario['id']}/baja")
        self.assertEqual(sin_csrf.status_code, 403)

        headers = {"X-CSRF-Token": _csrf_api(c)}
        baja = c.post(f"/api/usuarios/{usuario['id']}/baja", headers=headers)
        self.assertEqual(baja.status_code, 200)
        self.assertEqual(baja.get_json()["estado"], "INACTIVO")

    # ========================================================================
    # 6. PENDIENTES RESUELTOS: MIGRACIONES, PAGINACIÓN, BACKENDS Y CATÁLOGO
    # ========================================================================

    def test_tc29_migraciones_versionadas_e_idempotentes(self):
        """TC-29: Aplica migraciones versionadas, las registra y soporta DB antiguas."""
        # Se deriva de la lista oficial para no romper al añadir migraciones nuevas.
        versiones_esperadas = [version for version, _, _ in database.MIGRACIONES]

        filas = database.listar_migraciones(self.db_path)
        self.assertEqual([f["version"] for f in filas], versiones_esperadas)
        self.assertTrue(all(f["nombre"] and f["aplicada_en"] for f in filas))

        # Reejecutar no duplica registros ni rompe el esquema.
        database.init_db(self.db_path)
        self.assertEqual(len(database.listar_migraciones(self.db_path)), len(versiones_esperadas))

        # Compatibilidad con una base creada por una versión anterior del MVP.
        legacy = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        legacy.close()
        try:
            conn = sqlite3.connect(legacy.name)
            conn.execute(
                """
                CREATE TABLE usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre_completo TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    rol TEXT NOT NULL,
                    estado TEXT NOT NULL,
                    fecha_registro TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE predicciones_calorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    tipo_actividad TEXT NOT NULL,
                    peso_kg REAL NOT NULL,
                    duracion_min REAL NOT NULL,
                    met REAL NOT NULL,
                    calorias_estimadas REAL NOT NULL,
                    fecha_registro TEXT NOT NULL
                )
                """
            )
            conn.commit()
            conn.close()

            database.init_db(legacy.name)
            conn = sqlite3.connect(legacy.name)
            columnas_usuarios = {f[1] for f in conn.execute("PRAGMA table_info(usuarios)")}
            columnas_predicciones = {f[1] for f in conn.execute("PRAGMA table_info(predicciones_calorias)")}
            versiones = [f[0] for f in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
            conn.close()

            self.assertIn("peso_preferido_kg", columnas_usuarios)
            self.assertIn("reset_token", columnas_usuarios)
            self.assertIn("fc_promedio", columnas_predicciones)
            self.assertIn("metodo_calculo", columnas_predicciones)
            self.assertEqual(versiones, versiones_esperadas)
        finally:
            if os.path.exists(legacy.name):
                os.unlink(legacy.name)

    def test_tc30_paginacion_del_historial(self):
        """TC-30: Pagina el historial (servicio y API) y suma totales filtrados."""
        u = self.servicio_usuarios.registrar_usuario("Pagina User", "pagina@uab.edu.bo", "clave1234")
        servicio = Willys_IA_CaloriaService(Willys_IA_CaloriaRepository(self.db_path))
        for i in range(5):
            servicio.predecir_y_guardar(u.id, f"Correr {i}", 70.0, 10.0, 10.0)

        pagina1 = servicio.listar_paginado(u.id, page=1, per_page=2)
        self.assertEqual(pagina1["total"], 5)
        self.assertEqual(pagina1["total_pages"], 3)
        self.assertEqual(pagina1["page"], 1)
        self.assertEqual(len(pagina1["items"]), 2)
        self.assertEqual([i.tipo_actividad for i in pagina1["items"]], ["Correr 4", "Correr 3"])
        self.assertAlmostEqual(pagina1["total_calorias"], 583.35, places=2)

        pagina3 = servicio.listar_paginado(u.id, page=3, per_page=2)
        self.assertEqual(len(pagina3["items"]), 1)
        self.assertEqual(pagina3["items"][0].tipo_actividad, "Correr 0")

        # Página fuera de rango: se ajusta a la última disponible.
        ultima = servicio.listar_paginado(u.id, page=99, per_page=2)
        self.assertEqual(ultima["page"], 3)

        filtrado = servicio.listar_paginado(u.id, q="correr 4", per_page=10)
        self.assertEqual(filtrado["total"], 1)
        self.assertEqual(len(filtrado["items"]), 1)

        # Contrato de la API: objeto con metadatos de paginación.
        c = self.client
        page = c.get("/registro")
        csrf = _csrf_from_html(page.get_data(as_text=True))
        c.post("/registro", data={"csrf_token": csrf, "nombre": "Api Pagina", "email": "apipagina@uab.edu.bo", "password": "clave1234"})
        headers = {"X-CSRF-Token": _csrf_api(c)}
        for actividad, met in (("Correr", 10), ("Yoga", 3), ("Baile", 5)):
            self.assertEqual(c.post("/api/calorias", json={
                "tipo_actividad": actividad, "peso_kg": 70, "duracion_min": 10, "met": met
            }, headers=headers).status_code, 201)

        data = c.get("/api/calorias?page=1&per_page=2").get_json()
        for clave in ("items", "total", "page", "per_page", "total_pages", "total_calorias"):
            self.assertIn(clave, data)
        self.assertEqual(data["total"], 3)
        self.assertEqual(data["total_pages"], 2)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(len(c.get("/api/calorias?page=2&per_page=2").get_json()["items"]), 1)
        self.assertEqual(c.get("/api/calorias?per_page=101").get_json()["per_page"], 100)

    def test_tc31_rate_limiting_backend_pluggable(self):
        """TC-31: Selecciona backend de rate limiting y cae a memoria sin Redis."""
        anterior_redis = os.environ.pop("REDIS_URL", None)
        try:
            self.assertEqual(security.backend_actual(), "memory")
            security.reconfigurar_backend("memory")
            self.assertEqual(security.backend_actual(), "memory")
            self.assertTrue(security.rate_limit("tc31:memoria", 1, 60))
            self.assertFalse(security.rate_limit("tc31:memoria", 1, 60))

            with contextlib.redirect_stdout(io.StringIO()):
                security.reconfigurar_backend("redis")  # sin REDIS_URL
                self.assertEqual(security.backend_actual(), "memory")

            with contextlib.redirect_stdout(io.StringIO()):
                security.reconfigurar_backend("auto")
                self.assertEqual(security.backend_actual(), "memory")
        finally:
            if anterior_redis is not None:
                os.environ["REDIS_URL"] = anterior_redis
            security.reconfigurar_backend("auto")

    def test_tc32_smtp_opcional_con_fallback_consola(self):
        """TC-32: Sin SMTP real (o con placeholders) imprime el enlace en consola."""
        claves = ("SMTP_HOST", "SMTP_USER", "SMTP_PASS")
        previos = {k: os.environ.pop(k, None) for k in claves}
        try:
            self.assertFalse(notificaciones.smtp_configurado())
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida):
                resultado = notificaciones.notificar_verificacion(
                    "demo@uab.edu.bo", "http://localhost/verificar/token-123"
                )
            self.assertEqual(resultado["canal"], "consola")
            self.assertFalse(resultado["enviado"])
            texto = salida.getvalue()
            self.assertIn("SIMULACIÓN LOCAL", texto)
            self.assertIn("verificar/token-123", texto)

            # Credenciales de ejemplo: se consideran no configuradas.
            os.environ.update({
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_USER": "tu_correo@gmail.com",
                "SMTP_PASS": "tu_contraseña",
            })
            self.assertFalse(notificaciones.smtp_configurado())
        finally:
            for clave in claves:
                os.environ.pop(clave, None)
            for clave, valor in previos.items():
                if valor is not None:
                    os.environ[clave] = valor

    def test_tc33_catalogo_met_versionado(self):
        """TC-33: El catálogo expone versión, fuente y revisión sin inventar datos."""
        meta = met_catalogo.metadatos_catalogo()
        self.assertEqual(meta["version"], met_catalogo.VERSION_CATALOGO)
        self.assertEqual(meta["revision"], met_catalogo.REVISION_CATALOGO)
        self.assertIn("Compendium", meta["fuente"])
        self.assertEqual(meta["estado_validacion"], met_catalogo.ESTADO_VALIDACION)
        self.assertEqual(meta["total_actividades"], len(met_catalogo.CATALOGO_MET))

        data = self.client.get("/api/met-catalogo").get_json()
        self.assertEqual(data["catalogo"]["version"], met_catalogo.VERSION_CATALOGO)
        self.assertEqual(data["catalogo"]["estado_validacion"], met_catalogo.ESTADO_VALIDACION)
        self.assertEqual(len(data["actividades"]), 15)
        self.assertTrue(all({"key", "nombre", "met"} <= set(a) for a in data["actividades"]))

    def test_tc34_desglose_explicable_en_api_y_dashboard(self):
        """TC-34: Fórmula, valores y resultado se exponen al crear, listar y ver un registro."""
        u = self.servicio_usuarios.registrar_usuario(
            "Desglose User", "desglose@uab.edu.bo", "clave1234"
        )
        servicio = Willys_IA_CaloriaService(Willys_IA_CaloriaRepository(self.db_path))

        item_met = servicio.predecir_y_guardar(u.id, "Correr", 70.0, 30.0, 10.0)
        desc_met = servicio.desglose_calculo(item_met)
        self.assertEqual(desc_met["metodo"], "MET")
        self.assertIn("MET × peso_kg", desc_met["formula"])
        self.assertEqual(desc_met["valores"]["peso_kg"], 70.0)
        self.assertEqual(desc_met["valores"]["duracion_min"], 30.0)
        self.assertAlmostEqual(desc_met["resultado_sin_redondear"], 350.0, places=2)
        self.assertAlmostEqual(desc_met["resultado"], item_met.calorias_estimadas, places=2)

        item_keytel = servicio.predecir_y_guardar(
            u.id, "Correr", 70.0, 30.0, 10.0, fc_promedio=150, edad=30, sexo="M"
        )
        desc_key = servicio.desglose_calculo(item_keytel)
        self.assertEqual(desc_key["metodo"], "KEYTEL")
        self.assertIn("0.6309", desc_key["formula"])
        self.assertIn("4.184", desc_key["sustitucion"])
        self.assertIn("kcal_por_minuto", desc_key)
        self.assertAlmostEqual(desc_key["resultado"], item_keytel.calorias_estimadas, places=2)
        self.assertEqual(servicio.serializar(item_met)["desglose"]["metodo"], "MET")

        # Contrato HTTP: POST, GET listado y GET detalle incluyen el desglose.
        c = self.client
        pagina_login = c.get("/login")
        csrf_login = _csrf_from_html(pagina_login.get_data(as_text=True))
        self.assertEqual(c.post("/login", data={
            "csrf_token": csrf_login,
            "email": "desglose@uab.edu.bo",
            "password": "clave1234",
        }).status_code, 302)
        headers = {"X-CSRF-Token": _csrf_api(c)}
        self.assertEqual(c.post("/api/perfil", json={"edad": 30, "sexo": "M"}, headers=headers).status_code, 200)
        creado = c.post("/api/calorias", json={
            "tipo_actividad": "Trotar", "peso_kg": 70, "duracion_min": 20,
            "met": 9.8, "fc_promedio": 145,
        }, headers=headers)
        self.assertEqual(creado.status_code, 201)
        datos = creado.get_json()
        self.assertEqual(datos["desglose"]["metodo"], "KEYTEL")
        self.assertAlmostEqual(datos["desglose"]["resultado"], datos["calorias_estimadas"], places=2)

        items = c.get("/api/calorias").get_json()["items"]
        self.assertTrue(items)
        self.assertTrue(all("desglose" in it for it in items))
        detalle = c.get(f"/api/calorias/{datos['id']}")
        self.assertEqual(detalle.status_code, 200)
        self.assertIn("sustitucion", detalle.get_json()["desglose"])

        html = c.get("/dashboard").get_data(as_text=True)
        self.assertIn("¿Cómo se hace el cálculo?", html)
        self.assertIn("Ver cálculo", html)
        self.assertIn("Borrar", html)

    def test_tc35_borrado_de_registro_con_sesion_csrf_y_propiedad(self):
        """TC-35: Borrar exige sesión y CSRF, y solo el dueño puede eliminar."""
        cliente_a = self.app.test_client()
        cliente_b = self.app.test_client()

        def registrar(cliente, nombre, email):
            pagina = cliente.get("/registro")
            csrf = _csrf_from_html(pagina.get_data(as_text=True))
            respuesta = cliente.post("/registro", data={
                "csrf_token": csrf, "nombre": nombre, "email": email, "password": "clave1234"
            })
            self.assertEqual(respuesta.status_code, 302)

        registrar(cliente_a, "Dueno User", "dueno@uab.edu.bo")
        registrar(cliente_b, "Otro User", "otro@uab.edu.bo")
        headers_a = {"X-CSRF-Token": _csrf_api(cliente_a)}
        headers_b = {"X-CSRF-Token": _csrf_api(cliente_b)}

        creado = cliente_a.post("/api/calorias", json={
            "tipo_actividad": "Correr", "peso_kg": 70, "duracion_min": 30, "met": 10
        }, headers=headers_a)
        self.assertEqual(creado.status_code, 201)
        registro_id = creado.get_json()["id"]

        # Sin sesión, sin CSRF y desde otra cuenta: ninguno puede borrar.
        self.assertEqual(self.client.delete(f"/api/calorias/{registro_id}").status_code, 401)
        self.assertEqual(cliente_a.delete(f"/api/calorias/{registro_id}").status_code, 403)
        self.assertEqual(
            cliente_b.delete(f"/api/calorias/{registro_id}", headers=headers_b).status_code, 404
        )
        self.assertEqual(cliente_b.get(f"/api/calorias/{registro_id}").status_code, 404)
        self.assertEqual(cliente_a.get(f"/api/calorias/{registro_id}").status_code, 200)

        borrado = cliente_a.delete(f"/api/calorias/{registro_id}", headers=headers_a)
        self.assertEqual(borrado.status_code, 200)
        self.assertTrue(borrado.get_json()["eliminado"])
        self.assertEqual(cliente_a.get("/api/calorias").get_json()["total"], 0)
        self.assertEqual(
            cliente_a.delete(f"/api/calorias/{registro_id}", headers=headers_a).status_code, 404
        )

    def test_tc36_papelera_y_restauracion_de_registros(self):
        """TC-36: Borrar mueve a papelera; el dueño puede ver el desglose y restaurar."""
        cliente = self.app.test_client()
        pagina = cliente.get("/registro")
        csrf = _csrf_from_html(pagina.get_data(as_text=True))
        self.assertEqual(cliente.post("/registro", data={
            "csrf_token": csrf, "nombre": "Papelera User",
            "email": "papelera@uab.edu.bo", "password": "clave1234",
        }).status_code, 302)
        headers = {"X-CSRF-Token": _csrf_api(cliente)}

        ids = []
        for i in range(2):
            creado = cliente.post("/api/calorias", json={
                "tipo_actividad": f"Correr {i}", "peso_kg": 70,
                "duracion_min": 20, "met": 10,
            }, headers=headers)
            self.assertEqual(creado.status_code, 201)
            ids.append(creado.get_json()["id"])

        borrado = cliente.delete(f"/api/calorias/{ids[0]}", headers=headers)
        self.assertEqual(borrado.status_code, 200)
        self.assertTrue(borrado.get_json()["en_papelera"])
        self.assertEqual(cliente.get("/api/calorias").get_json()["total"], 1)

        papelera = cliente.get("/api/calorias/papelera")
        self.assertEqual(papelera.status_code, 200)
        datos = papelera.get_json()
        self.assertEqual(datos["total"], 1)
        self.assertTrue(datos["items"][0]["eliminado"])
        self.assertTrue(datos["items"][0]["fecha_eliminacion"])
        self.assertIn("desglose", datos["items"][0])

        # El detalle de un registro propio en papelera sigue siendo consultable.
        detalle = cliente.get(f"/api/calorias/{ids[0]}")
        self.assertEqual(detalle.status_code, 200)
        self.assertTrue(detalle.get_json()["eliminado"])
        self.assertEqual(cliente.get(f"/api/calorias/{ids[1]}").get_json()["eliminado"], False)

        self.assertEqual(
            cliente.post(f"/api/calorias/{ids[0]}/restaurar").status_code, 403
        )
        restaurado = cliente.post(f"/api/calorias/{ids[0]}/restaurar", headers=headers)
        self.assertEqual(restaurado.status_code, 200)
        self.assertTrue(restaurado.get_json()["restaurado"])
        self.assertFalse(restaurado.get_json()["registro"]["eliminado"])
        self.assertEqual(cliente.get("/api/calorias/papelera").get_json()["total"], 0)
        self.assertEqual(cliente.get("/api/calorias").get_json()["total"], 2)
        self.assertEqual(
            cliente.post(f"/api/calorias/{ids[0]}/restaurar", headers=headers).status_code, 404
        )

    def test_tc37_borrado_definitivo_y_vaciado_de_papelera(self):
        """TC-37: Borrado definitivo y vaciado solo afectan a la papelera del usuario."""
        cliente_a = self.app.test_client()
        cliente_b = self.app.test_client()

        def registrar(cliente, nombre, email):
            pagina = cliente.get("/registro")
            csrf = _csrf_from_html(pagina.get_data(as_text=True))
            self.assertEqual(cliente.post("/registro", data={
                "csrf_token": csrf, "nombre": nombre, "email": email, "password": "clave1234"
            }).status_code, 302)

        registrar(cliente_a, "Purga A", "purga-a@uab.edu.bo")
        registrar(cliente_b, "Purga B", "purga-b@uab.edu.bo")
        headers_a = {"X-CSRF-Token": _csrf_api(cliente_a)}
        headers_b = {"X-CSRF-Token": _csrf_api(cliente_b)}

        ids_a = []
        for i in range(2):
            creado = cliente_a.post("/api/calorias", json={
                "tipo_actividad": f"Yoga {i}", "peso_kg": 60, "duracion_min": 15, "met": 3,
            }, headers=headers_a)
            self.assertEqual(creado.status_code, 201)
            ids_a.append(creado.get_json()["id"])
        creado_b = cliente_b.post("/api/calorias", json={
            "tipo_actividad": "Baile", "peso_kg": 65, "duracion_min": 10, "met": 5,
        }, headers=headers_b)
        self.assertEqual(creado_b.status_code, 201)

        for registro_id in ids_a:
            self.assertEqual(
                cliente_a.delete(f"/api/calorias/{registro_id}", headers=headers_a).status_code, 200
            )
        self.assertEqual(cliente_a.get("/api/calorias/papelera").get_json()["total"], 2)

        # Otro usuario ni siquiera ve el registro en papelera.
        self.assertEqual(
            cliente_b.delete(
                f"/api/calorias/{ids_a[0]}/definitivo", headers=headers_b
            ).status_code, 404
        )
        self.assertEqual(
            cliente_b.delete(f"/api/calorias/{ids_a[0]}/definitivo").status_code, 403
        )

        definitivo = cliente_a.delete(
            f"/api/calorias/{ids_a[0]}/definitivo", headers=headers_a
        )
        self.assertEqual(definitivo.status_code, 200)
        self.assertTrue(definitivo.get_json()["eliminado_definitivamente"])
        self.assertEqual(cliente_a.get("/api/calorias/papelera").get_json()["total"], 1)
        self.assertEqual(
            cliente_a.delete(
                f"/api/calorias/{ids_a[0]}/definitivo", headers=headers_a
            ).status_code, 404
        )

        # Vaciar solo afecta a la papelera propia; B conserva su registro activo.
        self.assertEqual(
            cliente_b.delete("/api/calorias/papelera", headers=headers_b).get_json()["eliminados"], 0
        )
        vaciado = cliente_a.delete("/api/calorias/papelera", headers=headers_a)
        self.assertEqual(vaciado.status_code, 200)
        self.assertEqual(vaciado.get_json()["eliminados"], 1)
        self.assertEqual(cliente_a.get("/api/calorias/papelera").get_json()["total"], 0)
        self.assertEqual(cliente_b.get("/api/calorias").get_json()["total"], 1)

        html = cliente_a.get("/dashboard").get_data(as_text=True)
        self.assertIn("Papelera de predicciones", html)
        self.assertIn("Restaurar", html)

        # Migración versionada 6: columnas de papelera presentes.
        conn = sqlite3.connect(self.db_path)
        try:
            columnas = {fila[1] for fila in conn.execute("PRAGMA table_info(predicciones_calorias)")}
        finally:
            conn.close()
        self.assertIn("eliminado", columnas)
        self.assertIn("fecha_eliminacion", columnas)
        self.assertIn(
            6, [m["version"] for m in database.listar_migraciones(self.db_path)]
        )


class TestRegresionLineal(unittest.TestCase):
    """TC-43 a TC-51: CSV, ecuación normal, métricas, gráficas y flujo con regresión."""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self._tmp.close()
        self.db_path = self._tmp.name
        database.configurar_db(self.db_path)
        database.init_db(self.db_path)
        security.reconfigurar_backend("memory")
        security.reset_rate_limits()
        self.repo_usuarios = Willys_IA_UsuarioRepository(self.db_path)
        self.servicio_usuarios = Willys_IA_UsuarioService(self.repo_usuarios)
        self.repo_calorias = Willys_IA_CaloriaRepository(self.db_path)
        self.app = crear_app()
        self.app.config["TESTING"] = True

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_tc43_dataset_csv_valido(self):
        """TC-43: el CSV existe, tiene X_1..X_4, Y y suficientes filas anonimizadas."""
        ruta = regresion_lineal.RUTA_DATASET
        self.assertTrue(os.path.isfile(ruta))
        with open(ruta, "r", encoding="utf-8-sig", newline="") as archivo:
            self.assertEqual(
                archivo.readline().strip(), "X_1,X_2,X_3,X_4,Y"
            )
        filas = regresion_lineal.cargar_dataset()
        self.assertGreaterEqual(len(filas), 50)
        self.assertEqual(set(filas[0]), {"X_1", "X_2", "X_3", "X_4", "Y"})
        self.assertTrue(all(100 <= f["X_2"] <= 250 for f in filas))

        # Un CSV sin Y debe rechazarse con un mensaje claro.
        malo = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8")
        try:
            malo.write("X_1,X_2,X_3,X_4\n70,170,30,45\n")
            malo.close()
            with self.assertRaises(ValueError) as contexto:
                regresion_lineal.cargar_dataset(malo.name)
            self.assertIn("Y", str(contexto.exception))
        finally:
            if os.path.exists(malo.name):
                os.unlink(malo.name)

    def test_tc44_ecuacion_normal_con_coeficientes_conocidos(self):
        """TC-44: X con unos, Xᵀ, XᵀX, XᵀY y β = (XᵀX)⁻¹XᵀY recuperan β exacto."""
        temporal = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8")
        try:
            escritor = csv.writer(temporal)
            escritor.writerow(["X_1", "X_2", "X_3", "X_4", "Y"])
            for x1, x2, x3, x4 in FILAS_EXACTAS:
                y = 10 + 2 * x1 + 3 * x2 - x3 + 4 * x4
                escritor.writerow([x1, x2, x3, x4, y])
            temporal.close()

            modelo = RegresionLineal(temporal.name)
            self.assertEqual(modelo.X.shape, (12, 5))
            self.assertEqual(modelo.XT.shape, (5, 12))
            self.assertEqual(modelo.XTX.shape, (5, 5))
            self.assertEqual(modelo.XTY.shape, (5, 1))
            self.assertEqual(modelo.beta.shape, (5, 1))
            self.assertTrue(np.allclose(modelo.X[:, 0], 1.0))
            self.assertTrue(np.allclose(modelo.XTX, modelo.XT @ modelo.X))
            self.assertTrue(np.allclose(modelo.XTY, modelo.XT @ modelo.Y))
            self.assertTrue(np.allclose(modelo.coeficientes(), [10, 2, 3, -1, 4]))
            self.assertAlmostEqual(modelo.predecir(70, 170, 35, 45), 10 + 140 + 510 - 35 + 180, places=4)
        finally:
            if os.path.exists(temporal.name):
                os.unlink(temporal.name)

    def test_tc45_metricas_mae_rmse_r2(self):
        """TC-45: MAE/RMSE/R² son calculados por el modelo y coherentes con el CSV."""
        exacto = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8")
        try:
            escritor = csv.writer(exacto)
            escritor.writerow(["X_1", "X_2", "X_3", "X_4", "Y"])
            for x1, x2, x3, x4 in FILAS_EXACTAS:
                escritor.writerow([x1, x2, x3, x4, 5 + 2 * x1 + x2 - x3 + 3 * x4])
            exacto.close()
            modelo = RegresionLineal(exacto.name)
            self.assertAlmostEqual(modelo.mae, 0.0, places=6)
            self.assertAlmostEqual(modelo.rmse, 0.0, places=6)
            self.assertAlmostEqual(modelo.r2, 1.0, places=6)
        finally:
            if os.path.exists(exacto.name):
                os.unlink(exacto.name)

        real = RegresionLineal()
        self.assertGreater(real.mae, 0)
        self.assertLess(real.mae, 10)
        self.assertLess(real.rmse, 10)
        self.assertGreater(real.r2, 0.9)

    def test_tc46_serializacion_para_analisis_y_graficas(self):
        """TC-46: la API expone matrices, interpretación, ecuación, métricas y 3 gráficas."""
        datos = RegresionLineal().serializar()
        self.assertEqual(datos["matrices"]["X"]["dimensiones"], [80, 5])
        self.assertEqual(datos["matrices"]["XT"]["dimensiones"], [5, 80])
        self.assertEqual(datos["matrices"]["Y"]["dimensiones"], [80, 1])
        self.assertEqual(datos["matrices"]["beta"]["dimensiones"], [5, 1])
        self.assertEqual(
            datos["ecuacion"], "Ŷ = β0 + β1X1 + β2X2 + β3X3 + β4X4"
        )
        self.assertIn("(XᵀX)⁻¹", datos["formula_normal"])
        self.assertEqual(len(datos["interpretacion"]), 5)
        self.assertIn("kg", datos["interpretacion"][1]["texto"])
        self.assertIn("cm", datos["interpretacion"][2]["texto"])
        self.assertEqual(set(datos["metricas"]), {"MAE", "RMSE", "R2"})
        self.assertEqual(len(datos["graficas"]["real_vs_predicho"]), 80)
        self.assertEqual(len(datos["graficas"]["residuos"]), 80)
        self.assertEqual(len(datos["graficas"]["impacto"]), 4)
        self.assertEqual(datos["dataset"]["filas"], 80)

    def test_tc47_migracion_v8_regresion(self):
        """TC-47: migración v8 agrega altura y snapshot a las tablas."""
        conn = sqlite3.connect(self.db_path)
        try:
            predicciones = {f[1] for f in conn.execute("PRAGMA table_info(predicciones_calorias)")}
            usuarios = {f[1] for f in conn.execute("PRAGMA table_info(usuarios)")}
        finally:
            conn.close()
        self.assertIn("altura_cm", predicciones)
        self.assertIn("modelo_snapshot", predicciones)
        self.assertIn("altura_preferida_cm", usuarios)
        self.assertIn(
            8, [m["version"] for m in database.listar_migraciones(self.db_path)]
        )

    def test_tc48_prediccion_regresion_y_desglose_historico(self):
        """TC-48: se guarda β como snapshot y el desglose histórico usa ese snapshot."""
        usuario = self.servicio_usuarios.registrar_usuario(
            "Reg User", "regresion@uab.edu.bo", "clave1234"
        )
        modelo = RegresionLineal()
        servicio = Willys_IA_CaloriaService(self.repo_calorias, modelo=modelo)

        item = servicio.predecir_y_guardar(
            usuario_id=usuario.id,
            tipo_actividad="Correr",
            peso_kg=70,
            duracion_min=45,
            met=9.8,
            edad=35,
            altura_cm=170,
        )
        self.assertEqual(item.metodo_calculo, "REGRESION")
        self.assertEqual(item.altura_cm, 170)
        self.assertIsNotNone(item.modelo_snapshot)
        self.assertEqual(len(json.loads(item.modelo_snapshot)["beta"]), 5)
        self.assertAlmostEqual(
            item.calorias_estimadas, round(max(modelo.predecir(70, 170, 35, 45), 0), 2), places=2
        )

        desglose = servicio.desglose_calculo(item)
        self.assertEqual(desglose["metodo"], "REGRESION")
        self.assertEqual(desglose["ecuacion"], "Ŷ = β0 + β1X1 + β2X2 + β3X3 + β4X4")
        self.assertTrue(desglose["snapshot_usado"])
        self.assertEqual(desglose["beta"], [round(b, 6) for b in modelo.coeficientes()])
        self.assertEqual(desglose["resultado"], round(item.calorias_estimadas, 2))
        self.assertEqual(len(desglose["contribuciones"]), 5)
        self.assertEqual(len(desglose["pasos"]), 5)

        # Si el CSV cambiara, el registro antiguo se explica con su β guardado.
        item.modelo_snapshot = json.dumps({"version": 1, "beta": [0, 0, 0, 0, 0]})
        otro = servicio.desglose_calculo(item)
        self.assertEqual(otro["beta"], [0, 0, 0, 0, 0])
        self.assertEqual(otro["resultado"], round(item.calorias_estimadas, 2))

    def test_tc49_endpoint_analisis_y_dashboard(self):
        """TC-49: /api/calorias/analisis exige sesión y el dashboard muestra sección y gráficas."""
        cliente = self.app.test_client()
        self.assertEqual(cliente.get("/api/calorias/analisis").status_code, 401)

        pagina = cliente.get("/registro")
        csrf = _csrf_from_html(pagina.get_data(as_text=True))
        cliente.post(
            "/registro",
            data={
                "csrf_token": csrf,
                "nombre": "Analisis User",
                "email": "analisis@uab.edu.bo",
                "password": "clave1234",
            },
        )
        html = cliente.get("/dashboard").get_data(as_text=True)
        self.assertIn("Análisis técnico · Regresión lineal múltiple", html)
        self.assertIn("chart-real-predicho", html)
        self.assertIn("chart-residuos", html)
        self.assertIn("chart-impacto", html)
        self.assertIn("chart.umd.min.js", html)
        self.assertIn("XᵀX", html)
        self.assertIn("MAE", html)

        respuesta = cliente.get("/api/calorias/analisis")
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.get_json()
        self.assertIn("matrices", datos)
        self.assertIn("metricas", datos)
        self.assertIn("graficas", datos)
        cliente.get("/logout")
        self.assertEqual(cliente.get("/api/calorias/analisis").status_code, 401)

    def test_tc50_flujo_completo_con_altura_del_perfil(self):
        """TC-50: perfil con altura → regresión → historial, papelera y restauración."""
        cliente = self.app.test_client()
        pagina = cliente.get("/registro")
        csrf = _csrf_from_html(pagina.get_data(as_text=True))
        cliente.post(
            "/registro",
            data={
                "csrf_token": csrf,
                "nombre": "Flujo Regresion",
                "email": "flujo.reg@uab.edu.bo",
                "password": "clave1234",
            },
        )
        csrf_api = _csrf_api(cliente)
        cabecera = {"X-CSRF-Token": csrf_api}
        perfil = cliente.post(
            "/api/perfil",
            json={
                "peso_preferido_kg": 70,
                "altura_preferida_cm": 172,
                "edad": 33,
                "sexo": "M",
            },
            headers=cabecera,
        )
        self.assertEqual(perfil.status_code, 200)
        self.assertEqual(perfil.get_json()["usuario"]["altura_preferida_cm"], 172)

        creada = cliente.post(
            "/api/calorias",
            json={
                "tipo_actividad": "Correr",
                "peso_kg": 70,
                "duracion_min": 50,
                "met": 9.8,
            },
            headers=cabecera,
        )
        self.assertEqual(creada.status_code, 201)
        item = creada.get_json()
        self.assertEqual(item["metodo_calculo"], "REGRESION")
        self.assertEqual(item["altura_cm"], 172)
        self.assertEqual(item["desglose"]["metodo"], "REGRESION")

        registro_id = str(item["id"])
        detalle = cliente.get("/api/calorias/" + registro_id).get_json()
        self.assertIn("β = (XᵀX)⁻¹", detalle["desglose"]["pasos"][0])

        borrar = cliente.delete("/api/calorias/" + registro_id, headers=cabecera)
        self.assertEqual(borrar.status_code, 200)
        papelera = cliente.get("/api/calorias/papelera").get_json()
        self.assertTrue(any(x["id"] == item["id"] for x in papelera["items"]))
        self.assertNotIn(
            item["id"], [x["id"] for x in cliente.get("/api/calorias").get_json()["items"]]
        )

        restaurar = cliente.post(
            "/api/calorias/" + registro_id + "/restaurar", headers=cabecera
        )
        self.assertEqual(restaurar.status_code, 200)
        self.assertTrue(
            any(x["id"] == item["id"] for x in cliente.get("/api/calorias").get_json()["items"])
        )

    def test_tc51_respaldo_met_keytel_sin_altura(self):
        """TC-51: sin altura se conservan Keytel y MET como respaldo del historial."""
        usuario = self.servicio_usuarios.registrar_usuario(
            "Fallback User", "fallback@uab.edu.bo", "clave1234"
        )
        servicio = Willys_IA_CaloriaService(self.repo_calorias, modelo=RegresionLineal())
        keytel = servicio.predecir_y_guardar(
            usuario_id=usuario.id,
            tipo_actividad="Correr",
            peso_kg=70,
            duracion_min=30,
            met=9.8,
            fc_promedio=150,
            edad=30,
            sexo="M",
        )
        self.assertEqual(keytel.metodo_calculo, "KEYTEL")
        self.assertIsNone(keytel.altura_cm)
        self.assertEqual(servicio.desglose_calculo(keytel)["metodo"], "KEYTEL")

        met = servicio.predecir_y_guardar(
            usuario_id=usuario.id,
            tipo_actividad="Caminar",
            peso_kg=70,
            duracion_min=30,
            met=4,
        )
        self.assertEqual(met.metodo_calculo, "MET")
        self.assertIsNone(met.modelo_snapshot)


class TestGoogleSignIn(unittest.TestCase):
    """TC-38 a TC-42: Google Sign-In opcional, vinculación y callback OAuth."""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self._tmp.close()
        self.db_path = self._tmp.name
        database.configurar_db(self.db_path)
        database.init_db(self.db_path)
        security.reconfigurar_backend("memory")
        security.reset_rate_limits()
        self.repo_usuarios = Willys_IA_UsuarioRepository(self.db_path)
        self.servicio_usuarios = Willys_IA_UsuarioService(self.repo_usuarios)
        self.app = crear_app()
        self.app.config["TESTING"] = True

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_tc38_migracion_google_signin(self):
        """TC-38: migración v7 agrega proveedor, google_sub y su índice único."""
        conn = sqlite3.connect(self.db_path)
        try:
            columnas = {fila[1] for fila in conn.execute("PRAGMA table_info(usuarios)")}
            indices = {fila[1] for fila in conn.execute("PRAGMA index_list(usuarios)")}
        finally:
            conn.close()
        self.assertIn("proveedor", columnas)
        self.assertIn("google_sub", columnas)
        self.assertIn("idx_usuarios_google_sub", indices)
        self.assertIn(
            7, [m["version"] for m in database.listar_migraciones(self.db_path)]
        )

    def test_tc39_boton_google_desactivado_sin_credenciales(self):
        """TC-39: sin credenciales el botón aparece desactivado con [POR DEFINIR]."""
        sin_google = {
            "GOOGLE_CLIENT_ID": "",
            "GOOGLE_CLIENT_SECRET": "",
            "GOOGLE_REDIRECT_URI": "",
        }
        cliente = self.app.test_client()
        with mock.patch.dict(os.environ, sin_google):
            html = cliente.get("/login").get_data(as_text=True)
            respuesta = cliente.get("/google/login")
        self.assertIn("Continuar con Google", html)
        self.assertIn("disabled", html)
        self.assertIn("POR DEFINIR", html)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Google Sign-In pendiente", respuesta.get_data(as_text=True))

    def test_tc40_vincular_cuenta_local_por_correo_google(self):
        """TC-40: un correo existente se vincula y conserva su contraseña e historial."""
        local = self.servicio_usuarios.registrar_usuario(
            "Usuario Local", "google-link@uab.edu.bo", "clave1234"
        )
        claims = {
            "sub": "google-sub-1001",
            "email": "GOOGLE-LINK@uab.edu.bo",
            "nombre": "Cuenta Google",
            "email_verificado": True,
        }
        vinculado = self.servicio_usuarios.autenticar_google(claims)
        self.assertEqual(vinculado.id, local.id)
        self.assertEqual(vinculado.proveedor, "GOOGLE")
        self.assertEqual(vinculado.google_sub, "google-sub-1001")
        self.assertTrue(vinculado.email_verificado)
        self.assertEqual(
            self.servicio_usuarios.autenticar(local.email, "clave1234").id, local.id
        )

        # Otro sub distinto no puede apropiarse del correo ya vinculado.
        with self.assertRaises(ValueError):
            self.servicio_usuarios.autenticar_google(
                {
                    "sub": "google-sub-otro",
                    "email": local.email,
                    "nombre": "Intruso",
                    "email_verificado": True,
                }
            )

    def test_tc41_crear_usuario_nuevo_desde_google(self):
        """TC-41: un correo nuevo crea cuenta GOOGLE; un sub repetido reingresa."""
        claims = {
            "sub": "google-sub-2002",
            "email": "nuevo.google@gmail.com",
            "nombre": "Nuevo Google",
            "email_verificado": True,
        }
        creado = self.servicio_usuarios.autenticar_google(claims)
        self.assertEqual(creado.proveedor, "GOOGLE")
        self.assertEqual(creado.email, "nuevo.google@gmail.com")
        self.assertTrue(creado.email_verificado)
        self.assertEqual(self.servicio_usuarios.autenticar_google(claims).id, creado.id)

        with self.assertRaises(ValueError):
            self.servicio_usuarios.autenticar_google(
                dict(claims, email_verificado=False)
            )

    def test_tc42_callback_google_valida_state_y_abre_sesion(self):
        """TC-42: el callback rechaza state inválido y entra con uno válido."""
        credenciales = {
            "GOOGLE_CLIENT_ID": "cliente-prueba",
            "GOOGLE_CLIENT_SECRET": "secreto-prueba",
            "GOOGLE_REDIRECT_URI": "http://127.0.0.1:5000/google/callback",
        }
        claims = {
            "sub": "google-sub-3003",
            "email": "callback@gmail.com",
            "nombre": "Usuario Callback",
            "email_verificado": True,
        }
        cliente = self.app.test_client()
        with mock.patch.dict(os.environ, credenciales), mock.patch(
            "main.google_auth.intercambiar_y_verificar", return_value=claims
        ):
            html = cliente.get("/login").get_data(as_text=True)
            self.assertIn('href="/google/login"', html)
            self.assertNotIn("disabled>Continuar con Google", html)

            inicio = cliente.get("/google/login")
            self.assertEqual(inicio.status_code, 302)
            self.assertIn("accounts.google.com", inicio.headers["Location"])

            invalido = cliente.get("/google/callback?state=malo&code=abc")
            self.assertEqual(invalido.status_code, 400)

            inicio2 = cliente.get("/google/login")
            state = re.search(r"[?&]state=([^&]+)", inicio2.headers["Location"]).group(1)
            correcto = cliente.get(
                "/google/callback?state=" + state + "&code=abc"
            )
            self.assertEqual(correcto.status_code, 302)
            self.assertIn("/dashboard", correcto.headers["Location"])
            self.assertEqual(cliente.get("/dashboard").status_code, 200)


class TestDeteccionDeRed(unittest.TestCase):
    """La app debe funcionar en cualquier WiFi, no solo en una red concreta."""

    def test_ips_locales_sin_loopback(self):
        import ipaddress
        from main import _ips_locales

        ips = _ips_locales()
        self.assertIsInstance(ips, list)
        self.assertEqual(len(ips), len(set(ips)))
        for valor in ips:
            direccion = ipaddress.ip_address(valor)
            self.assertEqual(direccion.version, 4)
            self.assertFalse(direccion.is_loopback)
            self.assertFalse(direccion.is_link_local)

    def test_ip_en_lan_es_utilizable(self):
        from main import _ip_en_lan

        valor = _ip_en_lan()
        self.assertTrue(valor)


if __name__ == "__main__":
    unittest.main()
