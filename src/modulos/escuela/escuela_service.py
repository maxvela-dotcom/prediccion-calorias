# -*- coding: utf-8 -*-
"""
Capa de Servicio / Negocio (Service Layer) — Módulo Escuela de Fútbol.
Willys_IA: aplica las reglas de docs/SPEC_ESCUELA.md y orquesta el repositorio.

Reglas implementadas en el MVP:
- RN-E01: el estudiante debe pertenecer a la sede y categoría de la sesión.
- RN-E02: no se permite doble asistencia en la misma sesión.
- RN-E03: QR y marca manual son equivalentes.
- RN-E04: el aviso de ausencia es idempotente por sesión y estudiante.
- RN-E05: 0 asistencias = 0 Bs; 1 o más = tarifa completa de la categoría.
- RN-E06: becado = 0 Bs (no se cobra).
- RN-E07: solo se puede marcar pagado/pendiente cuando hay monto a cobrar.
"""

import re
import secrets
from datetime import date, datetime
from typing import Dict, List, Optional

from werkzeug.security import check_password_hash, generate_password_hash

from modulos.escuela.escuela_model import (
    Willys_IA_Cobro,
    Willys_IA_Estudiante,
    Willys_IA_Sesion,
)
from modulos.escuela.escuela_repository import Willys_IA_EscuelaRepository

_PATRON_PERIODO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class Willys_IA_EscuelaService:
    """Willys_IA: casos de uso del registro y control de asistencias."""

    def __init__(self, repositorio: Optional[Willys_IA_EscuelaRepository] = None):
        self._repo = repositorio if repositorio is not None else Willys_IA_EscuelaRepository()

    @property
    def repositorio(self) -> Willys_IA_EscuelaRepository:
        return self._repo

    # ------------------------------------------------------------------
    # Utilidades de validación
    # ------------------------------------------------------------------

    @staticmethod
    def _validar_fecha(fecha: str) -> str:
        try:
            datetime.strptime((fecha or "").strip(), "%Y-%m-%d")
        except ValueError as err:
            raise ValueError("La fecha debe tener formato AAAA-MM-DD.") from err
        return fecha.strip()

    @staticmethod
    def _validar_hora(hora: str) -> str:
        try:
            datetime.strptime((hora or "").strip(), "%H:%M")
        except ValueError as err:
            raise ValueError("La hora debe tener formato HH:MM.") from err
        return hora.strip()

    @staticmethod
    def _validar_periodo(periodo: str) -> str:
        periodo_limpio = (periodo or "").strip()
        if not _PATRON_PERIODO.match(periodo_limpio):
            raise ValueError("El periodo debe tener formato AAAA-MM (ej. 2026-11).")
        return periodo_limpio

    @staticmethod
    def _entero(valor, campo: str) -> int:
        try:
            return int(valor)
        except (TypeError, ValueError) as err:
            raise ValueError(f"El campo '{campo}' debe ser un número entero.") from err

    @staticmethod
    def _texto(valor, campo: str, minimo: int = 2, maximo: int = 120) -> str:
        """Willys_IA: normaliza texto obligatorio y valida su longitud."""
        texto = (valor or "").strip() if isinstance(valor, str) else ""
        if len(texto) < minimo:
            raise ValueError(
                f"El campo '{campo}' debe tener al menos {minimo} caracteres."
            )
        if len(texto) > maximo:
            raise ValueError(
                f"El campo '{campo}' no puede superar {maximo} caracteres."
            )
        return texto

    @staticmethod
    def _booleano(valor) -> bool:
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, (int, float)):
            return valor != 0
        return str(valor or "").strip().lower() in ("1", "true", "on", "si", "sí", "yes")

    @staticmethod
    def _validar_usuario(usuario: str) -> str:
        limpio = (usuario or "").strip().lower()
        if not re.match(r"^[a-z0-9._-]{3,30}$", limpio):
            raise ValueError(
                "El usuario debe tener entre 3 y 30 caracteres y solo puede "
                "usar letras minúsculas, números, punto, guion o guion bajo."
            )
        return limpio

    @staticmethod
    def _validar_clave(clave: str) -> str:
        valor = clave or ""
        if len(valor) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres.")
        if len(valor) > 128:
            raise ValueError("La contraseña no puede superar 128 caracteres.")
        return valor

    @staticmethod
    def _publico(fila: Optional[Dict]) -> Optional[Dict]:
        """Quita el hash de contraseña antes de devolver una cuenta a la web."""
        if not fila:
            return None
        return {clave: valor for clave, valor in fila.items() if clave != "password_hash"}

    def _nuevo_token_qr(self) -> str:
        """Genera un código EF-XXXXXXXX único para el alumno."""
        for _ in range(20):
            token = "EF-" + secrets.token_hex(4).upper()
            if not self._repo.obtener_estudiante_por_token(token):
                return token
        raise ValueError("No se pudo generar un código QR único. Intenta de nuevo.")

    # ------------------------------------------------------------------
    # Contexto y sesiones
    # ------------------------------------------------------------------

    def contexto(self, periodo: Optional[str] = None) -> Dict:
        """Willys_IA: datos iniciales para el panel web."""
        hoy = date.today().isoformat()
        periodo_actual = periodo or date.today().strftime("%Y-%m")
        return {
            "hoy": hoy,
            "periodo_actual": self._validar_periodo(periodo_actual),
            "sedes": [s.to_dict() for s in self._repo.listar_sedes()],
            "categorias": [c.to_dict() for c in self._repo.listar_categorias()],
            "estudiantes": [e.to_dict() for e in self._repo.listar_estudiantes()],
            "sesiones_hoy": [
                s.to_dict() for s in self._repo.listar_sesiones(fecha=hoy, limite=20)
            ],
            "resumen": self.resumen(periodo_actual),
        }

    def listar_sesiones(self, fecha: Optional[str] = None, limite: int = 30) -> List[Dict]:
        if fecha:
            fecha = self._validar_fecha(fecha)
        return [s.to_dict() for s in self._repo.listar_sesiones(fecha=fecha, limite=limite)]

    def crear_sesion(
        self,
        sede_id: int,
        categoria_id: int,
        fecha: str,
        hora: str,
        entrenador: str,
    ) -> Willys_IA_Sesion:
        """Abre (o reutiliza) la sesión de una sede/categoría en una fecha y hora."""
        sede_id = self._entero(sede_id, "sede_id")
        categoria_id = self._entero(categoria_id, "categoria_id")
        fecha = self._validar_fecha(fecha)
        hora = self._validar_hora(hora)
        entrenador = (entrenador or "").strip()
        if len(entrenador) < 3:
            raise ValueError("El nombre del entrenador debe tener al menos 3 caracteres.")

        sedes = {s.id for s in self._repo.listar_sedes()}
        categorias = {c.id for c in self._repo.listar_categorias()}
        if sede_id not in sedes:
            raise ValueError("La sede seleccionada no existe.")
        if categoria_id not in categorias:
            raise ValueError("La categoría seleccionada no existe.")

        return self._repo.crear_sesion(sede_id, categoria_id, fecha, hora, entrenador)

    def detalle_sesion(self, sesion_id: int) -> Dict:
        """Presentes, ausentes y avisos de una sesión."""
        sesion = self._repo.obtener_sesion(self._entero(sesion_id, "sesion_id"))
        if not sesion:
            raise ValueError("La sesión no existe.")

        asistencias = self._repo.listar_asistencias(sesion.id)
        ausentes = self._repo.listar_ausentes(sesion.id)
        avisos = self._repo.listar_avisos(sesion_id=sesion.id)

        return {
            "sesion": sesion.to_dict(),
            "presentes": [
                {
                    "estudiante_id": int(a["estudiante_id"]),
                    "estudiante": a["estudiante_nombre"],
                    "metodo": a["metodo"],
                    "registrada_en": a["registrada_en"],
                }
                for a in asistencias
            ],
            "ausentes": [
                {"estudiante_id": e.id, "estudiante": e.nombre} for e in ausentes
            ],
            "avisos": [a.to_dict() for a in avisos],
            "stats": {
                "presentes": len(asistencias),
                "ausentes": len(ausentes),
                "avisos_pendientes": sum(1 for a in avisos if a.estado == "PENDIENTE"),
            },
        }

    # ------------------------------------------------------------------
    # Asistencia
    # ------------------------------------------------------------------

    def registrar_asistencia(
        self,
        sesion_id: int,
        qr_token: Optional[str] = None,
        estudiante_id: Optional[int] = None,
        metodo: str = "QR",
    ) -> Dict:
        """
        Registra una asistencia por QR o por marca manual.
        Ambas vías son equivalentes (RN-E03) y no se permite duplicado (RN-E02).
        """
        metodo_limpio = (metodo or "QR").strip().upper()
        if metodo_limpio not in ("QR", "MANUAL"):
            raise ValueError("El método debe ser 'QR' o 'MANUAL'.")

        sesion = self._repo.obtener_sesion(self._entero(sesion_id, "sesion_id"))
        if not sesion:
            raise ValueError("La sesión no existe.")

        if qr_token:
            estudiante = self._repo.obtener_estudiante_por_token(qr_token)
        elif estudiante_id is not None:
            estudiante = self._repo.obtener_estudiante(self._entero(estudiante_id, "estudiante_id"))
        else:
            raise ValueError("Debe indicar un código QR o un estudiante.")

        if not estudiante:
            raise ValueError("No se encontró un estudiante con ese código QR o ID.")
        if estudiante.estado != "ACTIVO":
            raise ValueError("El estudiante está inactivo y no puede registrar asistencia.")
        if estudiante.sede_id != sesion.sede_id or estudiante.categoria_id != sesion.categoria_id:
            raise ValueError(
                "El estudiante no pertenece a la sede y categoría de esta sesión."
            )
        if self._repo.obtener_asistencia(sesion.id, estudiante.id):
            raise ValueError(
                f"{estudiante.nombre} ya está registrado en esta sesión."
            )

        asistencia_id = self._repo.registrar_asistencia(sesion.id, estudiante.id, metodo_limpio)
        return {
            "id": asistencia_id,
            "estudiante_id": estudiante.id,
            "estudiante": estudiante.nombre,
            "metodo": metodo_limpio,
            "mensaje": "Asistencia registrada",
        }

    # ------------------------------------------------------------------
    # Avisos
    # ------------------------------------------------------------------

    def generar_avisos(self, sesion_id: int) -> Dict:
        """Crea avisos pendientes para todos los ausentes de la sesión."""
        sesion = self._repo.obtener_sesion(self._entero(sesion_id, "sesion_id"))
        if not sesion:
            raise ValueError("La sesión no existe.")

        ausentes = self._repo.listar_ausentes(sesion.id)
        creados = sum(1 for e in ausentes if self._repo.crear_aviso(sesion.id, e.id))
        return {
            "ausentes": len(ausentes),
            "creados": creados,
            "ya_existian": len(ausentes) - creados,
            "pendientes": self._repo.contar_avisos_pendientes(),
        }

    def listar_avisos(self, estado: Optional[str] = None) -> List[Dict]:
        avisos = self._repo.listar_avisos(estado=estado)
        resultado = []
        for aviso in avisos:
            datos = aviso.to_dict()
            datos["mensaje"] = (
                f"El alumno {aviso.estudiante_nombre} faltó al entrenamiento del "
                f"{aviso.fecha} ({aviso.categoria_nombre} · {aviso.sede_nombre}). "
                "Por favor, justifique la falta y solicite la recuperación."
            )
            resultado.append(datos)
        return resultado

    def marcar_aviso_enviado(self, aviso_id: int) -> Dict:
        aviso_id = self._entero(aviso_id, "aviso_id")
        if not self._repo.marcar_aviso_enviado(aviso_id):
            raise ValueError("El aviso no existe o ya fue marcado como enviado.")
        aviso = self._repo.obtener_aviso(aviso_id)
        return aviso.to_dict() if aviso else {"id": aviso_id, "estado": "ENVIADA"}

    # ------------------------------------------------------------------
    # Cobros
    # ------------------------------------------------------------------

    def calcular_cobro(self, estudiante: Willys_IA_Estudiante, periodo: str) -> Willys_IA_Cobro:
        """Aplica RN-E05 y RN-E06 al estudiante para el periodo indicado."""
        periodo = self._validar_periodo(periodo)
        asistencias = self._repo.contar_asistencias_periodo(estudiante.id, periodo)

        if estudiante.becado:
            monto, motivo = 0.0, "BECA"
        elif asistencias == 0:
            monto, motivo = 0.0, "SIN_ASISTENCIA"
        else:
            monto, motivo = float(estudiante.precio_mensual), "ASISTENCIA"

        pago = self._repo.obtener_pago(estudiante.id, periodo)
        if monto <= 0:
            estado_pago = "NO_APLICA"
            fecha_pago = ""
        elif pago:
            estado_pago = pago["estado"]
            fecha_pago = pago["fecha_pago"] or ""
        else:
            estado_pago = "PENDIENTE"
            fecha_pago = ""

        return Willys_IA_Cobro(
            estudiante_id=estudiante.id,
            nombre=estudiante.nombre,
            categoria=estudiante.categoria_nombre,
            sede=estudiante.sede_nombre,
            asistencias=asistencias,
            monto=monto,
            motivo=motivo,
            estado_pago=estado_pago,
            fecha_pago=fecha_pago,
        )

    def listar_cobros(self, periodo: str) -> Dict:
        periodo = self._validar_periodo(periodo)
        cobros = [
            self.calcular_cobro(e, periodo) for e in self._repo.listar_estudiantes()
        ]
        return {
            "periodo": periodo,
            "cobros": [c.to_dict() for c in cobros],
            "resumen": {
                "estudiantes": len(cobros),
                "becados": sum(1 for c in cobros if c.motivo == "BECA"),
                "sin_asistencia": sum(1 for c in cobros if c.motivo == "SIN_ASISTENCIA"),
                "pagados": sum(1 for c in cobros if c.estado_pago == "PAGADO"),
                "pendientes": sum(1 for c in cobros if c.estado_pago == "PENDIENTE"),
                "total_facturado": round(sum(c.monto for c in cobros), 2),
                "total_cobrado": round(
                    sum(c.monto for c in cobros if c.estado_pago == "PAGADO"), 2
                ),
                "total_pendiente": round(
                    sum(c.monto for c in cobros if c.estado_pago == "PENDIENTE"), 2
                ),
            },
        }

    def marcar_pago(self, estudiante_id: int, periodo: str, estado: str) -> Dict:
        """Marca un cobro como PAGADO o PENDIENTE (RN-E07)."""
        periodo = self._validar_periodo(periodo)
        estado_limpio = (estado or "").strip().upper()
        if estado_limpio not in ("PAGADO", "PENDIENTE"):
            raise ValueError("El estado de pago debe ser 'PAGADO' o 'PENDIENTE'.")

        estudiante = self._repo.obtener_estudiante(self._entero(estudiante_id, "estudiante_id"))
        if not estudiante:
            raise ValueError("El estudiante no existe.")

        cobro = self.calcular_cobro(estudiante, periodo)
        if cobro.monto <= 0:
            raise ValueError(
                "No hay monto a cobrar para este estudiante en el periodo "
                f"({cobro.motivo.replace('_', ' ').lower()})."
            )

        fecha_pago = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if estado_limpio == "PAGADO" else ""
        self._repo.guardar_pago(
            estudiante.id, periodo, cobro.monto, estado_limpio, fecha_pago
        )
        return self.calcular_cobro(estudiante, periodo).to_dict()

    # ------------------------------------------------------------------
    # Resumen / KPIs
    # ------------------------------------------------------------------

    def resumen(self, periodo: Optional[str] = None) -> Dict:
        periodo = self._validar_periodo(periodo or date.today().strftime("%Y-%m"))
        hoy = date.today().isoformat()
        cobros = self.listar_cobros(periodo)["resumen"]
        return {
            "periodo": periodo,
            "estudiantes_activos": self._repo.contar_estudiantes_activos(),
            "sesiones_hoy": self._repo.contar_sesiones_hoy(hoy),
            "presentes_hoy": self._repo.contar_asistencias_hoy(hoy),
            "ausentes_hoy": self._repo.contar_ausentes_hoy(hoy),
            "avisos_pendientes": self._repo.contar_avisos_pendientes(),
            "total_pendiente": cobros["total_pendiente"],
            "total_cobrado": cobros["total_cobrado"],
        }

    # ------------------------------------------------------------------
    # Willys_IA: acceso compartido (login por rol) y vista del alumno
    # ------------------------------------------------------------------

    def autenticar(self, usuario: str, clave: str) -> Optional[Dict]:
        """Verifica credenciales de la app compartida. Nunca devuelve el hash."""
        fila = self._repo.obtener_usuario_por_nombre(usuario)
        if not fila or not fila["activo"]:
            return None
        if not check_password_hash(fila["password_hash"], clave or ""):
            return None
        return {
            "id": int(fila["id"]),
            "usuario": fila["usuario"],
            "nombre": fila["nombre"],
            "rol": fila["rol"],
            "estudiante_id": fila["estudiante_id"],
        }

    def mi_registro(self, estudiante_id: int, periodo: Optional[str] = None) -> Dict:
        """
        Solo lectura del propio alumno: QR, asistencias, faltas y cobro del mes.
        No expone información de otros estudiantes.
        """
        periodo = self._validar_periodo(periodo or date.today().strftime("%Y-%m"))
        estudiante = self._repo.obtener_estudiante(self._entero(estudiante_id, "estudiante_id"))
        if not estudiante:
            raise ValueError("No hay un alumno asociado a este usuario.")

        historial = self._repo.listar_historial_estudiante(estudiante.id, periodo)
        asistencias = sum(1 for h in historial if h["asistio"])
        faltas = len(historial) - asistencias
        avisos = [
            a.to_dict()
            for a in self._repo.listar_avisos()
            if a.estudiante_id == estudiante.id and a.fecha.startswith(periodo)
        ]
        return {
            "periodo": periodo,
            "estudiante": estudiante.to_dict(),
            "cobro": self.calcular_cobro(estudiante, periodo).to_dict(),
            "historial": historial,
            "avisos": avisos,
            "resumen": {
                "sesiones": len(historial),
                "asistencias": asistencias,
                "faltas": faltas,
            },
        }

    # ------------------------------------------------------------------
    # Willys_IA: primer arranque, altas de alumnos y gestión de cuentas
    # ------------------------------------------------------------------

    def hay_usuarios(self) -> bool:
        """True cuando ya existe al menos una cuenta (primer arranque completado)."""
        return self._repo.contar_usuarios_escuela() > 0

    def asegurar_catalogo_minimo(self) -> Dict:
        """
        Crea sedes y categorías base solo si el catálogo está vacío.
        Así la base puede empezar en cero y quedar operativa en el setup.
        """
        if not self._repo.listar_sedes():
            self._repo.crear_sede("Sede Central")
            self._repo.crear_sede("Sede Norte")
        if not self._repo.listar_categorias():
            self._repo.crear_categoria("Sub-8", 400.0)
            self._repo.crear_categoria("Sub-15", 500.0)
            self._repo.crear_categoria("Sub-18", 600.0)
        return {
            "sedes": [s.to_dict() for s in self._repo.listar_sedes()],
            "categorias": [c.to_dict() for c in self._repo.listar_categorias()],
        }

    def crear_admin_inicial(self, usuario: str, nombre: str, clave: str) -> Dict:
        """Crea el administrador del primer arranque. Solo funciona con la base vacía."""
        if self.hay_usuarios():
            raise ValueError(
                "Ya existe una cuenta en el sistema. Inicia sesión con tu usuario."
            )

        usuario_limpio = self._validar_usuario(usuario)
        nombre_limpio = self._texto(nombre, "nombre completo", 3, 120)
        clave_limpia = self._validar_clave(clave)

        creado = self._repo.crear_usuario_escuela(
            usuario_limpio,
            nombre_limpio,
            generate_password_hash(clave_limpia),
            "ADMIN",
        )
        if not creado:
            raise ValueError("Ese usuario ya existe. Elige otro nombre de usuario.")

        self.asegurar_catalogo_minimo()
        return self._publico(self._repo.obtener_usuario_por_nombre(usuario_limpio))

    def crear_cuenta_personal(
        self, usuario: str, nombre: str, clave: str, rol: str = "ENTRENADOR"
    ) -> Dict:
        """Alta de una cuenta ADMIN o ENTRENADOR desde el panel de administración."""
        rol_limpio = (rol or "").strip().upper()
        if rol_limpio not in ("ADMIN", "ENTRENADOR"):
            raise ValueError("El rol debe ser ADMIN o ENTRENADOR.")

        usuario_limpio = self._validar_usuario(usuario)
        nombre_limpio = self._texto(nombre, "nombre completo", 3, 120)
        clave_limpia = self._validar_clave(clave)

        if self._repo.obtener_usuario_por_nombre(usuario_limpio):
            raise ValueError("Ese nombre de usuario ya está en uso.")

        creado = self._repo.crear_usuario_escuela(
            usuario_limpio,
            nombre_limpio,
            generate_password_hash(clave_limpia),
            rol_limpio,
        )
        if not creado:
            raise ValueError("No se pudo crear la cuenta. Revisa los datos.")
        return self._publico(self._repo.obtener_usuario_por_nombre(usuario_limpio))

    def crear_estudiante(
        self,
        nombre: str,
        categoria_id: int,
        sede_id: int,
        becado: bool = False,
        usuario: Optional[str] = None,
        clave: Optional[str] = None,
    ) -> Dict:
        """
        Alta manual de un alumno. Si se indican usuario y clave, crea también
        su cuenta de acceso (rol ALUMNO) vinculada al alumno.
        """
        nombre_limpio = self._texto(nombre, "nombre del alumno", 3, 120)
        categoria_id = self._entero(categoria_id, "categoría")
        sede_id = self._entero(sede_id, "sede")

        categorias = {c.id for c in self._repo.listar_categorias()}
        sedes = {s.id for s in self._repo.listar_sedes()}
        if categoria_id not in categorias:
            raise ValueError("La categoría seleccionada no existe.")
        if sede_id not in sedes:
            raise ValueError("La sede seleccionada no existe.")

        usuario_limpio = None
        clave_limpia = None
        if usuario or clave:
            if not (usuario and clave):
                raise ValueError(
                    "Para crear la cuenta del alumno completa usuario y contraseña."
                )
            usuario_limpio = self._validar_usuario(usuario)
            clave_limpia = self._validar_clave(clave)
            if self._repo.obtener_usuario_por_nombre(usuario_limpio):
                raise ValueError("Ese nombre de usuario ya está en uso.")

        estudiante = self._repo.crear_estudiante(
            nombre_limpio,
            categoria_id,
            sede_id,
            self._nuevo_token_qr(),
            becado=self._booleano(becado),
        )

        cuenta = None
        if usuario_limpio and clave_limpia:
            self._repo.crear_usuario_escuela(
                usuario_limpio,
                nombre_limpio,
                generate_password_hash(clave_limpia),
                "ALUMNO",
                estudiante.id,
            )
            cuenta = self._publico(
                self._repo.obtener_usuario_por_nombre(usuario_limpio)
            )

        return {"estudiante": estudiante.to_dict(), "cuenta": cuenta}

    def crear_cuenta_alumno(
        self, estudiante_id: int, usuario: str, clave: str
    ) -> Dict:
        """Crea una cuenta de acceso para un alumno que ya está registrado."""
        estudiante = self._repo.obtener_estudiante(
            self._entero(estudiante_id, "estudiante_id")
        )
        if not estudiante:
            raise ValueError("El estudiante no existe.")

        usuario_limpio = self._validar_usuario(usuario)
        clave_limpia = self._validar_clave(clave)
        if self._repo.obtener_usuario_por_nombre(usuario_limpio):
            raise ValueError("Ese nombre de usuario ya está en uso.")

        self._repo.crear_usuario_escuela(
            usuario_limpio,
            estudiante.nombre,
            generate_password_hash(clave_limpia),
            "ALUMNO",
            estudiante.id,
        )
        return self._publico(self._repo.obtener_usuario_por_nombre(usuario_limpio))

    def listar_cuentas(self) -> List[Dict]:
        """Cuentas existentes, sin hashes de contraseña."""
        return [
            {clave: valor for clave, valor in fila.items() if clave != "password_hash"}
            for fila in self._repo.listar_usuarios_detalle()
        ]

    def cambiar_clave(self, usuario: str, clave: str) -> Dict:
        usuario_limpio = self._validar_usuario(usuario)
        clave_limpia = self._validar_clave(clave)
        if not self._repo.cambiar_password_usuario(
            usuario_limpio, generate_password_hash(clave_limpia)
        ):
            raise ValueError("La cuenta no existe.")
        return self._publico(self._repo.obtener_usuario_por_nombre(usuario_limpio))

    def crear_sede(self, nombre: str) -> Dict:
        nombre_limpio = self._texto(nombre, "nombre de la sede", 3, 80)
        existentes = {s.nombre.strip().lower() for s in self._repo.listar_sedes()}
        if nombre_limpio.lower() in existentes:
            raise ValueError("Ya existe una sede con ese nombre.")
        return self._repo.crear_sede(nombre_limpio).to_dict()

    def crear_categoria(self, nombre: str, precio_mensual) -> Dict:
        nombre_limpio = self._texto(nombre, "nombre de la categoría", 2, 80)
        try:
            precio = float(precio_mensual)
        except (TypeError, ValueError) as err:
            raise ValueError("La tarifa mensual debe ser un número.") from err
        if precio <= 0:
            raise ValueError("La tarifa mensual debe ser mayor que cero.")

        existentes = {c.nombre.strip().lower() for c in self._repo.listar_categorias()}
        if nombre_limpio.lower() in existentes:
            raise ValueError("Ya existe una categoría con ese nombre.")
        return self._repo.crear_categoria(nombre_limpio, round(precio, 2)).to_dict()

    def dar_baja_estudiante(self, estudiante_id: int) -> Dict:
        """Baja lógica: conserva el historial y bloquea nuevas asistencias."""
        estudiante_id = self._entero(estudiante_id, "estudiante_id")
        if not self._repo.eliminar_estudiante(estudiante_id):
            raise ValueError("El estudiante no existe.")
        return {"id": estudiante_id, "estado": "INACTIVO"}
