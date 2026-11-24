# -*- coding: utf-8 -*-
"""
Pruebas del módulo Escuela de Fútbol (Willys_IA).
Valida las reglas RN-E01 a RN-E07 del contrato docs/SPEC_ESCUELA.md
y los endpoints Flask del blueprint.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import database
from flask import Flask

from modulos.escuela.escuela_qr import generar_qr_svg
from modulos.escuela.escuela_repository import Willys_IA_EscuelaRepository
from modulos.escuela.escuela_service import Willys_IA_EscuelaService
from modulos.escuela import escuela_controller
from modulos.escuela.escuela_controller import bp_escuela


class TestEscuelaFutbol(unittest.TestCase):
    """Willys_IA: suite de reglas de negocio y capa de control."""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self._tmp.close()
        self.db_path = self._tmp.name
        database.configurar_db(self.db_path)
        database.init_db(self.db_path)

        self.repo = Willys_IA_EscuelaRepository(self.db_path)
        self.servicio = Willys_IA_EscuelaService(self.repo)

        self.sede = self.repo.crear_sede("Sede Test")
        self.sede2 = self.repo.crear_sede("Sede Norte Test")
        self.cat15 = self.repo.crear_categoria("Sub-15", 500.0)
        self.cat18 = self.repo.crear_categoria("Sub-18", 600.0)

        self.juan = self.repo.crear_estudiante(
            "Juan Pérez", self.cat15.id, self.sede.id, "EF-TEST01"
        )
        self.ana = self.repo.crear_estudiante(
            "Ana Rojas", self.cat15.id, self.sede.id, "EF-TEST02"
        )
        self.luis = self.repo.crear_estudiante(
            "Luis Vega", self.cat18.id, self.sede.id, "EF-TEST03"
        )
        self.beca = self.repo.crear_estudiante(
            "Beca Estudiante", self.cat15.id, self.sede.id, "EF-TEST04", becado=True
        )

        self.sesion = self.repo.crear_sesion(
            self.sede.id, self.cat15.id, "2026-11-10", "16:00", "Prof. Ramiro"
        )
        self.sesion18 = self.repo.crear_sesion(
            self.sede.id, self.cat18.id, "2026-11-10", "18:00", "Prof. Lucía"
        )

        # Willys_IA: cuentas propias de la prueba (sin datos demo).
        self.servicio.crear_admin_inicial("admin", "Administración", "admin1234")
        self.servicio.crear_cuenta_personal(
            "entrenador", "Prof. Ramiro Salazar", "entren1234", "ENTRENADOR"
        )
        self.servicio.crear_cuenta_alumno(self.juan.id, "alumno", "alumno1234")

    def tearDown(self):
        database.configurar_db(None)
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Asistencia
    # ------------------------------------------------------------------

    def test_registra_asistencia_con_qr(self):
        resultado = self.servicio.registrar_asistencia(
            self.sesion.id, qr_token="EF-TEST01", metodo="QR"
        )
        self.assertEqual(resultado["estudiante"], "Juan Pérez")
        self.assertEqual(resultado["metodo"], "QR")
        self.assertEqual(resultado["mensaje"], "Asistencia registrada")

        detalle = self.servicio.detalle_sesion(self.sesion.id)
        self.assertEqual(detalle["stats"]["presentes"], 1)
        self.assertEqual(detalle["presentes"][0]["estudiante"], "Juan Pérez")

    def test_rechaza_doble_registro(self):
        self.servicio.registrar_asistencia(self.sesion.id, qr_token="EF-TEST01")
        with self.assertRaises(ValueError) as ctx:
            self.servicio.registrar_asistencia(self.sesion.id, qr_token="EF-TEST01")
        self.assertIn("ya está registrado", str(ctx.exception))

    def test_marca_manual_equivale_a_qr(self):
        resultado = self.servicio.registrar_asistencia(
            self.sesion.id, estudiante_id=self.juan.id, metodo="MANUAL"
        )
        self.assertEqual(resultado["metodo"], "MANUAL")
        detalle = self.servicio.detalle_sesion(self.sesion.id)
        self.assertEqual(detalle["presentes"][0]["metodo"], "MANUAL")

    def test_rechaza_estudiante_de_otra_categoria(self):
        with self.assertRaises(ValueError) as ctx:
            self.servicio.registrar_asistencia(
                self.sesion.id, estudiante_id=self.luis.id, metodo="MANUAL"
            )
        self.assertIn("no pertenece", str(ctx.exception))

    def test_ausentes_excluye_presentes(self):
        self.servicio.registrar_asistencia(self.sesion.id, qr_token="EF-TEST01")
        detalle = self.servicio.detalle_sesion(self.sesion.id)
        nombres = [a["estudiante"] for a in detalle["ausentes"]]
        self.assertNotIn("Juan Pérez", nombres)
        self.assertIn("Ana Rojas", nombres)
        self.assertIn("Beca Estudiante", nombres)
        self.assertEqual(detalle["stats"]["ausentes"], 2)

    def test_rechaza_token_inexistente(self):
        with self.assertRaises(ValueError) as ctx:
            self.servicio.registrar_asistencia(self.sesion.id, qr_token="EF-NOEXISTE")
        self.assertIn("No se encontró", str(ctx.exception))

    # ------------------------------------------------------------------
    # Cobros
    # ------------------------------------------------------------------

    def test_cobro_cero_sin_asistencias(self):
        cobro = self.servicio.calcular_cobro(self.ana, "2026-11")
        self.assertEqual(cobro.asistencias, 0)
        self.assertEqual(cobro.monto, 0.0)
        self.assertEqual(cobro.motivo, "SIN_ASISTENCIA")
        self.assertEqual(cobro.estado_pago, "NO_APLICA")

    def test_cobro_precio_completo_con_una_asistencia(self):
        self.servicio.registrar_asistencia(self.sesion.id, qr_token="EF-TEST01")
        cobro = self.servicio.calcular_cobro(self.juan, "2026-11")
        self.assertEqual(cobro.asistencias, 1)
        self.assertEqual(cobro.monto, 500.0)
        self.assertEqual(cobro.motivo, "ASISTENCIA")
        self.assertEqual(cobro.estado_pago, "PENDIENTE")

    def test_becado_no_paga(self):
        self.servicio.registrar_asistencia(self.sesion.id, qr_token="EF-TEST04")
        cobro = self.servicio.calcular_cobro(self.beca, "2026-11")
        self.assertEqual(cobro.asistencias, 1)
        self.assertEqual(cobro.monto, 0.0)
        self.assertEqual(cobro.motivo, "BECA")

    def test_marcar_pagado_y_pendiente(self):
        self.servicio.registrar_asistencia(self.sesion.id, qr_token="EF-TEST01")
        pagado = self.servicio.marcar_pago(self.juan.id, "2026-11", "PAGADO")
        self.assertEqual(pagado["estado_pago"], "PAGADO")
        self.assertTrue(pagado["fecha_pago"])

        pendiente = self.servicio.marcar_pago(self.juan.id, "2026-11", "PENDIENTE")
        self.assertEqual(pendiente["estado_pago"], "PENDIENTE")
        self.assertEqual(pendiente["fecha_pago"], "")

    def test_no_marca_pago_sin_monto(self):
        with self.assertRaises(ValueError) as ctx:
            self.servicio.marcar_pago(self.ana.id, "2026-11", "PAGADO")
        self.assertIn("No hay monto a cobrar", str(ctx.exception))

    def test_resumen_cobros(self):
        self.servicio.registrar_asistencia(self.sesion.id, qr_token="EF-TEST01")
        self.servicio.registrar_asistencia(self.sesion.id, qr_token="EF-TEST04")
        self.servicio.marcar_pago(self.juan.id, "2026-11", "PAGADO")

        datos = self.servicio.listar_cobros("2026-11")
        self.assertEqual(datos["resumen"]["total_facturado"], 500.0)
        self.assertEqual(datos["resumen"]["total_cobrado"], 500.0)
        self.assertEqual(datos["resumen"]["total_pendiente"], 0.0)
        self.assertEqual(datos["resumen"]["becados"], 1)
        self.assertEqual(datos["resumen"]["pagados"], 1)

    def test_periodo_invalido(self):
        with self.assertRaises(ValueError):
            self.servicio.listar_cobros("2026-13")

    # ------------------------------------------------------------------
    # Avisos
    # ------------------------------------------------------------------

    def test_generar_avisos_es_idempotente(self):
        self.servicio.registrar_asistencia(self.sesion.id, qr_token="EF-TEST01")
        primero = self.servicio.generar_avisos(self.sesion.id)
        self.assertEqual(primero["ausentes"], 2)
        self.assertEqual(primero["creados"], 2)

        segundo = self.servicio.generar_avisos(self.sesion.id)
        self.assertEqual(segundo["creados"], 0)
        self.assertEqual(segundo["ya_existian"], 2)

        avisos = self.servicio.listar_avisos("PENDIENTE")
        self.assertEqual(len(avisos), 2)
        self.assertIn("faltó al entrenamiento", avisos[0]["mensaje"])

        enviado = self.servicio.marcar_aviso_enviado(avisos[0]["id"])
        self.assertEqual(enviado["estado"], "ENVIADA")
        self.assertEqual(len(self.servicio.listar_avisos("PENDIENTE")), 1)

    # ------------------------------------------------------------------
    # QR
    # ------------------------------------------------------------------

    def test_generar_qr_svg(self):
        svg = generar_qr_svg("EF-TEST01")
        self.assertIsInstance(svg, bytes)
        self.assertGreater(len(svg), 200)
        self.assertIn(b"<svg", svg)

    # ------------------------------------------------------------------
    # Integración Flask
    # ------------------------------------------------------------------

    def _app(self):
        ruta_templates = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "src", "templates")
        )
        app = Flask(__name__, template_folder=ruta_templates)
        app.secret_key = "prueba-escuela"
        app.register_blueprint(bp_escuela)
        app.config.update(TESTING=True)
        return app

    def _cliente(self, rol="ADMIN", estudiante_id=None):
        cliente = self._app().test_client()
        with cliente.session_transaction() as sesion:
            sesion["escuela_usuario_id"] = 1
            sesion["escuela_usuario"] = rol.lower()
            sesion["escuela_nombre"] = "Usuario de prueba"
            sesion["escuela_rol"] = rol
            sesion["escuela_estudiante_id"] = (
                estudiante_id if estudiante_id is not None
                else (self.juan.id if rol == "ALUMNO" else None)
            )
        return cliente

    def _cliente_sin_sesion(self):
        return self._app().test_client()

    def test_pagina_escuela_responde(self):
        cliente = self._cliente()
        respuesta = cliente.get("/escuela")
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.get_data(as_text=True)
        self.assertIn("Escuela de Fútbol", html)
        self.assertIn('data-tab="altas"', html)

    def test_api_contexto_y_qr(self):
        cliente = self._cliente()
        contexto = cliente.get("/api/escuela/contexto")
        self.assertEqual(contexto.status_code, 200)
        datos = contexto.get_json()
        self.assertEqual(len(datos["sedes"]), 2)
        self.assertEqual(len(datos["categorias"]), 2)
        self.assertGreaterEqual(len(datos["estudiantes"]), 4)

        qr = cliente.get(f"/api/escuela/estudiantes/{self.juan.id}/qr.svg")
        self.assertEqual(qr.status_code, 200)
        self.assertIn("image/svg+xml", qr.headers["Content-Type"])

    def test_api_registrar_asistencia(self):
        cliente = self._cliente()
        respuesta = cliente.post(
            f"/api/escuela/sesiones/{self.sesion.id}/asistencia",
            json={"qr_token": "EF-TEST01", "metodo": "QR"},
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.get_json()["estudiante"], "Juan Pérez")

        duplicado = cliente.post(
            f"/api/escuela/sesiones/{self.sesion.id}/asistencia",
            json={"qr_token": "EF-TEST01", "metodo": "QR"},
        )
        self.assertEqual(duplicado.status_code, 400)
        self.assertIn("ya está registrado", duplicado.get_json()["error"])

    def test_api_cobros_y_pago(self):
        cliente = self._cliente()
        cliente.post(
            f"/api/escuela/sesiones/{self.sesion.id}/asistencia",
            json={"qr_token": "EF-TEST01", "metodo": "QR"},
        )
        cobros = cliente.get("/api/escuela/cobros?periodo=2026-11")
        self.assertEqual(cobros.status_code, 200)
        self.assertEqual(cobros.get_json()["periodo"], "2026-11")

        pago = cliente.post(
            "/api/escuela/cobros",
            json={"estudiante_id": self.juan.id, "periodo": "2026-11", "estado": "PAGADO"},
        )
        self.assertEqual(pago.status_code, 200)
        self.assertEqual(pago.get_json()["cobro"]["estado_pago"], "PAGADO")

    # ------------------------------------------------------------------
    # Altas, cuentas, catálogo y primer arranque
    # ------------------------------------------------------------------

    def test_setup_crea_admin_y_catalogo_en_base_vacia(self):
        temporal = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temporal.close()
        original = escuela_controller.servicio_escuela_singleton
        try:
            database.init_db(temporal.name)
            servicio = Willys_IA_EscuelaService(
                Willys_IA_EscuelaRepository(temporal.name)
            )
            escuela_controller.servicio_escuela_singleton = servicio
            self.assertFalse(servicio.hay_usuarios())

            cliente = self._cliente_sin_sesion()
            pagina = cliente.get("/escuela/setup")
            self.assertEqual(pagina.status_code, 200)
            self.assertIn("Primer arranque", pagina.get_data(as_text=True))

            creado = cliente.post(
                "/escuela/setup",
                data={
                    "nombre": "Ana Morales",
                    "usuario": "ana.morales",
                    "clave": "secreto1",
                    "clave2": "secreto1",
                },
            )
            self.assertEqual(creado.status_code, 302)
            self.assertTrue(servicio.hay_usuarios())
            self.assertEqual(len(servicio.repositorio.listar_sedes()), 2)
            self.assertEqual(len(servicio.repositorio.listar_categorias()), 3)
            with cliente.session_transaction() as sesion:
                self.assertEqual(sesion["escuela_rol"], "ADMIN")

            segundo = self._cliente_sin_sesion().get("/escuela/setup")
            self.assertEqual(segundo.status_code, 302)
            self.assertIn("/escuela/login", segundo.headers["Location"])
        finally:
            escuela_controller.servicio_escuela_singleton = original
            database.configurar_db(self.db_path)
            try:
                os.unlink(temporal.name)
            except OSError:
                pass

    def test_crear_alumno_con_y_sin_cuenta(self):
        con_cuenta = self.servicio.crear_estudiante(
            "Nuevo Alumno",
            self.cat15.id,
            self.sede.id,
            usuario="nuevo.alumno",
            clave="clave123",
        )
        self.assertEqual(con_cuenta["estudiante"]["nombre"], "Nuevo Alumno")
        self.assertTrue(con_cuenta["estudiante"]["qr_token"].startswith("EF-"))
        self.assertEqual(con_cuenta["cuenta"]["rol"], "ALUMNO")
        self.assertEqual(
            con_cuenta["cuenta"]["estudiante_id"], con_cuenta["estudiante"]["id"]
        )
        sesion = self.servicio.autenticar("nuevo.alumno", "clave123")
        self.assertEqual(sesion["rol"], "ALUMNO")

        sin_cuenta = self.servicio.crear_estudiante(
            "Alumno Sin Cuenta", self.cat15.id, self.sede.id
        )
        self.assertIsNone(sin_cuenta["cuenta"])

    def test_cuenta_personal_y_cambio_de_clave(self):
        cuenta = self.servicio.crear_cuenta_personal(
            "auxiliar", "Auxiliar Uno", "clave123", "ADMIN"
        )
        self.assertEqual(cuenta["rol"], "ADMIN")
        self.assertNotIn("password_hash", cuenta)

        self.servicio.cambiar_clave("auxiliar", "nueva123")
        self.assertIsNotNone(self.servicio.autenticar("auxiliar", "nueva123"))
        self.assertIsNone(self.servicio.autenticar("auxiliar", "clave123"))

    def test_catalogo_y_baja_logica(self):
        sede = self.servicio.crear_sede("Sede Sur")
        self.assertEqual(sede["nombre"], "Sede Sur")
        with self.assertRaises(ValueError):
            self.servicio.crear_sede("Sede Sur")

        categoria = self.servicio.crear_categoria("Sub-10", 450)
        self.assertEqual(categoria["precio_mensual"], 450.0)
        with self.assertRaises(ValueError):
            self.servicio.crear_categoria("Sub-10", 500)
        with self.assertRaises(ValueError):
            self.servicio.crear_categoria("Sub-12", 0)

        self.servicio.dar_baja_estudiante(self.luis.id)
        self.assertEqual(
            self.repo.obtener_estudiante(self.luis.id).estado, "INACTIVO"
        )

    def test_api_altas_y_cuentas_admin(self):
        cliente = self._cliente()

        alumno = cliente.post(
            "/api/escuela/estudiantes",
            json={
                "nombre": "Alumno API",
                "sede_id": self.sede.id,
                "categoria_id": self.cat15.id,
                "usuario": "alumno.api",
                "clave": "clave123",
            },
        )
        self.assertEqual(alumno.status_code, 201)
        self.assertEqual(alumno.get_json()["cuenta"]["rol"], "ALUMNO")

        cuentas = cliente.get("/api/escuela/usuarios")
        self.assertEqual(cuentas.status_code, 200)
        self.assertTrue(
            any(c["usuario"] == "alumno.api" for c in cuentas.get_json()["cuentas"])
        )

        personal = cliente.post(
            "/api/escuela/usuarios",
            json={
                "nombre": "Profe Nuevo",
                "usuario": "profe.nuevo",
                "clave": "clave123",
                "rol": "ENTRENADOR",
            },
        )
        self.assertEqual(personal.status_code, 201)

        clave = cliente.post(
            "/api/escuela/usuarios/profe.nuevo/clave", json={"clave": "otra123"}
        )
        self.assertEqual(clave.status_code, 200)

        sede = cliente.post("/api/escuela/sedes", json={"nombre": "Sede Sur"})
        self.assertEqual(sede.status_code, 201)
        categoria = cliente.post(
            "/api/escuela/categorias",
            json={"nombre": "Sub-10", "precio_mensual": 450},
        )
        self.assertEqual(categoria.status_code, 201)

        baja = cliente.post(f"/api/escuela/estudiantes/{self.luis.id}/baja")
        self.assertEqual(baja.status_code, 200)

    def test_entrenador_no_puede_gestionar_altas(self):
        cliente = self._cliente(rol="ENTRENADOR")
        self.assertEqual(
            cliente.post(
                "/api/escuela/estudiantes",
                json={
                    "nombre": "No Permitido",
                    "sede_id": self.sede.id,
                    "categoria_id": self.cat15.id,
                },
            ).status_code,
            403,
        )
        self.assertEqual(cliente.get("/api/escuela/usuarios").status_code, 403)
        self.assertEqual(
            cliente.post(
                "/api/escuela/sedes", json={"nombre": "Sede Prohibida"}
            ).status_code,
            403,
        )
        html = cliente.get("/escuela").get_data(as_text=True)
        self.assertNotIn('data-tab="altas"', html)

    def test_api_respaldo_descarga_copia_valida(self):
        cliente = self._cliente()
        respuesta = cliente.get("/escuela/respaldo")
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data.startswith(b"SQLite format 3"))
        self.assertIn(
            "attachment", respuesta.headers.get("Content-Disposition", "")
        )

        self.assertEqual(
            self._cliente(rol="ENTRENADOR").get("/escuela/respaldo").status_code,
            403,
        )

    def test_respaldo_consistente_y_automatico(self):
        import shutil
        import sqlite3

        carpeta = tempfile.mkdtemp(prefix="escuela-respaldo-")
        try:
            database.configurar_db(os.path.join(carpeta, "app.db"))
            database.init_db()

            # Base sin cuentas: no hay nada que respaldar todavía.
            self.assertIsNone(database.respaldo_automatico())

            servicio = Willys_IA_EscuelaService(
                Willys_IA_EscuelaRepository(os.path.join(carpeta, "app.db"))
            )
            servicio.crear_admin_inicial("jefa", "Jefa Escuela", "clave123")

            copia = os.path.join(carpeta, "copia.db")
            database.crear_respaldo(copia)
            self.assertTrue(os.path.exists(copia))

            conn = sqlite3.connect(copia)
            try:
                self.assertEqual(
                    conn.execute("SELECT COUNT(*) FROM ef_usuarios").fetchone()[0],
                    1,
                )
            finally:
                conn.close()

            automatico = database.respaldo_automatico()
            self.assertIsNotNone(automatico)
            self.assertTrue(os.path.exists(automatico))
            self.assertTrue(
                automatico.startswith(os.path.join(carpeta, "respaldos"))
            )
            # No duplica el respaldo del mismo día.
            self.assertEqual(database.respaldo_automatico(), automatico)
        finally:
            database.configurar_db(self.db_path)
            shutil.rmtree(carpeta, ignore_errors=True)

    # ------------------------------------------------------------------
    # App compartida: login, roles y vista del alumno
    # ------------------------------------------------------------------

    def test_login_con_roles(self):
        cliente = self._cliente_sin_sesion()
        self.assertEqual(cliente.get("/escuela/login").status_code, 200)

        correcto = cliente.post(
            "/escuela/login", data={"usuario": "admin", "clave": "admin1234"}
        )
        self.assertEqual(correcto.status_code, 302)
        with cliente.session_transaction() as sesion:
            self.assertEqual(sesion["escuela_rol"], "ADMIN")

        incorrecto = self._cliente_sin_sesion().post(
            "/escuela/login", data={"usuario": "admin", "clave": "clave-mala"}
        )
        self.assertEqual(incorrecto.status_code, 401)
        self.assertIn("incorrectos", incorrecto.get_data(as_text=True))

    def test_sin_sesion_protege_panel_y_api(self):
        cliente = self._cliente_sin_sesion()
        pagina = cliente.get("/escuela")
        self.assertEqual(pagina.status_code, 302)
        self.assertIn("/escuela/login", pagina.headers["Location"])
        self.assertEqual(cliente.get("/api/escuela/contexto").status_code, 401)

    def test_entrenador_no_puede_cobrar_ni_marcar_avisos(self):
        cliente = self._cliente(rol="ENTRENADOR")
        self.assertEqual(cliente.get("/api/escuela/contexto").status_code, 200)
        self.assertEqual(
            cliente.get("/api/escuela/cobros?periodo=2026-11").status_code, 403
        )
        self.assertEqual(
            cliente.post(
                "/api/escuela/cobros",
                json={"estudiante_id": self.juan.id, "periodo": "2026-11", "estado": "PAGADO"},
            ).status_code,
            403,
        )
        self.assertEqual(cliente.post("/api/escuela/avisos/1/enviado").status_code, 403)
        html = cliente.get("/escuela").get_data(as_text=True)
        self.assertNotIn('<button class="tab" data-tab="cobros">', html)
        self.assertNotIn('id="panel-cobros"', html)

    def test_alumno_ve_solo_su_registro(self):
        cliente = self._cliente(rol="ALUMNO")
        pagina = cliente.get("/escuela")
        self.assertEqual(pagina.status_code, 200)
        self.assertIn("Mi registro", pagina.get_data(as_text=True))
        self.assertEqual(cliente.get("/api/escuela/contexto").status_code, 403)

        propio = cliente.get("/api/escuela/mi?periodo=2026-11")
        self.assertEqual(propio.status_code, 200)
        datos = propio.get_json()
        self.assertEqual(datos["estudiante"]["id"], self.juan.id)
        self.assertIn("cobro", datos)
        self.assertIn("historial", datos)
        self.assertGreaterEqual(datos["resumen"]["sesiones"], 1)

        self.assertEqual(
            cliente.get(f"/api/escuela/estudiantes/{self.juan.id}/qr.svg").status_code, 200
        )
        self.assertEqual(
            cliente.get(f"/api/escuela/estudiantes/{self.ana.id}/qr.svg").status_code, 403
        )


if __name__ == "__main__":
    unittest.main()
