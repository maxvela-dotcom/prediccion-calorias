# -*- coding: utf-8 -*-
"""
Capa de Lógica de Negocio de Predicción de Calorías (Service Layer).
Willys_IA: Calcula calorías estimadas y aplica reglas de validación.

Métodos soportados:
- REGRESION: ecuación normal β = (XᵀX)⁻¹ XᵀY entrenada con data/dataset_calorias.csv.
  Se usa cuando están los 4 predictores (peso, altura, edad y minutos).
- MET:   calorías = MET × peso_kg × (duración_min / 60)
- KEYTEL: usa frecuencia cardíaca promedio + edad + sexo (si están disponibles).
  MET/Keytel se conservan como respaldo para registros antiguos sin altura.
"""

import csv
import io
import json
import math
from typing import Dict, List, Optional, Tuple
from modulos.prediccion_calorias.caloria_model import Willys_IA_CaloriaModel
from modulos.prediccion_calorias.caloria_repository import Willys_IA_CaloriaRepository
from modulos.prediccion_calorias.met_catalogo import met_valido, obtener_met
from modulos.prediccion_calorias.regresion_lineal import (
    ECUACION_SIMBOLICA,
    RegresionLineal,
    predecir_con_coeficientes,
)


FORMULA_MET = "MET × peso_kg × (duracion_min / 60)"
FORMULA_KEYTEL_M = "((-55.0969 + 0.6309·FC + 0.1988·peso + 0.2017·edad) / 4.184) × duracion_min"
FORMULA_KEYTEL_F = "((-20.4022 + 0.4472·FC - 0.1263·peso + 0.0740·edad) / 4.184) × duracion_min"
NOTA_ESTIMACION = "Estimación educativa con fórmulas publicadas; no sustituye una valoración médica."
NOTA_REGRESION = (
    "Regresión lineal múltiple entrenada con data/dataset_calorias.csv mediante "
    "β = (XᵀX)⁻¹ XᵀY. Estimación educativa; no sustituye una valoración médica."
)


class Willys_IA_CaloriaService:
    """
    Willys_IA: Servicio de predicción de calorías.
    Reglas definidas:
    - peso_kg > 0 y <= 500; duración_min > 0 y <= 1440; MET en rango válido (0.5 a 20).
    - Si no se provee MET válido y la actividad existe en catálogo, se usa su MET.
    - Si hay altura y edad, se aplica la regresión entrenada desde el CSV;
      si falta alguno de esos predictores se mantiene Keytel (FC/edad/sexo) o MET.
    """

    def __init__(
        self,
        repositorio: Optional[Willys_IA_CaloriaRepository] = None,
        modelo: Optional[RegresionLineal] = None,
    ):
        self._repo = repositorio if repositorio is not None else Willys_IA_CaloriaRepository()
        self._modelo = modelo

    # ------------------------------------------------------------------
    # Modelo de regresión (carga diferida)
    # ------------------------------------------------------------------

    @property
    def modelo(self) -> RegresionLineal:
        """Entrena (una sola vez) el modelo desde el CSV de `data/`."""
        if self._modelo is None:
            self._modelo = RegresionLineal()
        return self._modelo

    def analisis(self) -> dict:
        """Datos completos del análisis técnico para el dashboard."""
        return self.modelo.serializar()

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    @staticmethod
    def _opcional_float(valor) -> Optional[float]:
        if valor in (None, ""):
            return None
        try:
            return float(valor)
        except (TypeError, ValueError):
            raise ValueError("La FC promedio debe ser un número válido.")

    @staticmethod
    def _opcional_int(valor) -> Optional[int]:
        if valor in (None, ""):
            return None
        try:
            return int(valor)
        except (TypeError, ValueError):
            raise ValueError("La edad debe ser un número entero.")

    @staticmethod
    def _opcional_altura(valor) -> Optional[float]:
        if valor in (None, ""):
            return None
        try:
            altura = float(valor)
        except (TypeError, ValueError):
            raise ValueError("La altura debe ser un número válido en centímetros.") from None
        if not (100 <= altura <= 250):
            raise ValueError("La altura debe estar entre 100 y 250 cm.")
        return altura

    @staticmethod
    def _normalizar_sexo(valor) -> Optional[str]:
        if valor in (None, ""):
            return None
        texto = str(valor).strip().upper()
        equivalencias = {
            "M": "M", "MASCULINO": "M", "HOMBRE": "M",
            "F": "F", "FEMENINO": "F", "MUJER": "F",
            "OTRO": "OTRO", "OTRA": "OTRO", "X": "OTRO",
        }
        return equivalencias.get(texto, texto)

    @staticmethod
    def _keytel_kcal_por_minuto(fc: float, peso: float, edad: int, sexo: str) -> float:
        """
        Ecuación de Keytel et al. (2005) para estimar gasto energético por FC.
        Hombres: (-55.0969 + 0.6309·FC + 0.1988·peso + 0.2017·edad) / 4.184
        Mujeres: (-20.4022 + 0.4472·FC - 0.1263·peso + 0.0740·edad) / 4.184
        """
        if sexo == "M":
            kcal_min = (-55.0969 + 0.6309 * fc + 0.1988 * peso + 0.2017 * edad) / 4.184
        else:
            kcal_min = (-20.4022 + 0.4472 * fc - 0.1263 * peso + 0.0740 * edad) / 4.184
        return max(kcal_min, 0.0)

    @staticmethod
    def _calcular_regresion(
        *,
        peso: float,
        altura: float,
        edad: float,
        dur: float,
        beta: List[float],
        met: Optional[float] = None,
        snapshot_usado: bool = False,
    ) -> Tuple[float, str, dict]:
        """Aplica los coeficientes entrenados y construye el desglose paso a paso."""
        coef = [float(v) for v in beta]
        if len(coef) != 5:
            raise ValueError("El vector β debe tener 5 coeficientes (β0..β4).")

        crudo = predecir_con_coeficientes(coef, peso, altura, edad, dur)
        calorias = max(crudo, 0.0)  # evita valores negativos por extrapolación

        entradas = [1.0, float(peso), float(altura), float(edad), float(dur)]
        aportes = [
            round(coef[i] * entradas[i], 4) for i in range(5)
        ]
        simbolos = ["β0", "β1·peso", "β2·altura", "β3·edad", "β4·minutos"]
        sustitucion = (
            f"{coef[0]:.4f} + {coef[1]:.4f}·{peso} + {coef[2]:.4f}·{altura} "
            f"+ {coef[3]:.4f}·{edad} + {coef[4]:.4f}·{dur}"
        )
        numerica = (
            f"Ŷ = {coef[0]:.4f} + {coef[1]:.4f}·X1 + {coef[2]:.4f}·X2 "
            f"+ {coef[3]:.4f}·X3 + {coef[4]:.4f}·X4"
        )

        desglose = {
            "metodo": "REGRESION",
            "formula": ECUACION_SIMBOLICA,
            "ecuacion": ECUACION_SIMBOLICA,
            "ecuacion_numerica": numerica,
            "sustitucion": sustitucion,
            "valores": {
                "peso_kg": float(peso),
                "altura_cm": float(altura),
                "edad": int(edad),
                "duracion_min": float(dur),
                "met": met,
                "fc_promedio": None,
                "sexo": None,
            },
            "beta": [round(v, 6) for v in coef],
            "vector_x": [round(v, 4) for v in entradas],
            "dimensiones": {
                "X": "n × 5 (columna de unos + 4 predictores)",
                "x": "1 × 5",
                "beta": "5 × 1",
            },
            "contribuciones": [
                {
                    "termino": simbolos[i],
                    "coeficiente": round(coef[i], 6),
                    "valor": round(entradas[i], 4),
                    "aporte": aportes[i],
                }
                for i in range(5)
            ],
            "pasos": [
                "1. Los coeficientes β se entrenaron con β = (XᵀX)⁻¹ XᵀY desde el CSV.",
                f"2. Vector de entrada x = [1, {peso}, {altura}, {edad}, {dur}].",
                f"3. Ŷ = x·β = {sustitucion}.",
                f"4. Suma de aportes = {' + '.join(str(v) for v in aportes)} → {round(calorias, 4)} kcal.",
                "5. Resultado presentado con 2 decimales.",
            ],
            "snapshot_usado": snapshot_usado,
            "resultado_sin_redondear": round(calorias, 4),
            "resultado": round(calorias, 2),
            "nota": NOTA_REGRESION,
        }
        return calorias, "REGRESION", desglose

    @classmethod
    def _calcular(
        cls,
        *,
        peso: float,
        dur: float,
        met: float,
        fc: Optional[float],
        edad: Optional[int],
        sexo: Optional[str],
        metodo_forzado: Optional[str] = None,
    ) -> Tuple[float, str, dict]:
        """
        Calcula las calorías y construye el desglose explicable de la operación.

        `metodo_forzado` permite reconstruir el cálculo de un registro ya guardado
        usando exactamente el método con el que se generó. Si faltan datos para
        Keytel, se degrada a MET sin fallar.
        """
        usar_keytel = (
            metodo_forzado == "KEYTEL"
            or (metodo_forzado is None and fc is not None and edad is not None and sexo in {"M", "F"})
        )
        if usar_keytel and fc is not None and edad is not None and sexo in {"M", "F"}:
            kcal_min = cls._keytel_kcal_por_minuto(fc, peso, edad, sexo)
            calorias = kcal_min * dur
            metodo = "KEYTEL"
            formula = FORMULA_KEYTEL_M if sexo == "M" else FORMULA_KEYTEL_F
            termino_fc = f"+ 0.6309·{fc}" if sexo == "M" else f"+ 0.4472·{fc}"
            termino_peso = f"+ 0.1988·{peso}" if sexo == "M" else f"- 0.1263·{peso}"
            termino_edad = f"+ 0.2017·{edad}" if sexo == "M" else f"+ 0.0740·{edad}"
            constante = "-55.0969" if sexo == "M" else "-20.4022"
            sustitucion = (
                f"(({constante} {termino_fc} {termino_peso} {termino_edad}) / 4.184) × {dur}"
            )
            derivado = {"kcal_por_minuto": round(kcal_min, 4)}
        else:
            calorias = met * peso * (dur / 60.0)
            metodo = "MET"
            formula = FORMULA_MET
            sustitucion = f"{met} × {peso} × ({dur} / 60)"
            derivado = {"horas": round(dur / 60.0, 4)}

        desglose = {
            "metodo": metodo,
            "formula": formula,
            "sustitucion": sustitucion,
            "valores": {
                "peso_kg": peso,
                "duracion_min": dur,
                "met": met,
                "fc_promedio": fc,
                "edad": edad,
                "sexo": sexo,
            },
            **derivado,
            "resultado_sin_redondear": round(calorias, 4),
            "resultado": round(calorias, 2),
            "nota": NOTA_ESTIMACION,
        }
        return calorias, metodo, desglose

    # ------------------------------------------------------------------
    # Predicción
    # ------------------------------------------------------------------

    def predecir_y_guardar(
        self,
        usuario_id: int,
        tipo_actividad: str,
        peso_kg: float,
        duracion_min: float,
        met: float,
        fc_promedio=None,
        edad=None,
        sexo=None,
        altura_cm=None,
    ) -> Willys_IA_CaloriaModel:
        tipo = (tipo_actividad or "").strip()
        try:
            peso = float(peso_kg)
            dur = float(duracion_min)
            met_val = float(met)
        except (TypeError, ValueError):
            raise ValueError("peso_kg, duracion_min y met deben ser números válidos.")

        # Si MET no es razonable, intentar resolver desde catálogo por actividad
        if not met_valido(met_val):
            ref = obtener_met(tipo)
            if ref is not None:
                met_val = ref
        if not met_valido(met_val):
            raise ValueError("MET inválido: debe estar entre 0.5 y 20.")

        if not (0 < peso <= 500):
            raise ValueError("El peso debe ser mayor a 0 y menor o igual a 500 kg.")
        if not (0 < dur <= 1440):
            raise ValueError("La duración debe ser mayor a 0 y menor o igual a 1440 minutos.")

        fc_val = self._opcional_float(fc_promedio)
        edad_val = self._opcional_int(edad)
        sexo_val = self._normalizar_sexo(sexo)
        altura_val = self._opcional_altura(altura_cm)

        if fc_val is not None and not (30 <= fc_val <= 220):
            raise ValueError("La FC promedio debe estar entre 30 y 220 ppm.")
        if edad_val is not None and not (10 <= edad_val <= 120):
            raise ValueError("La edad debe estar entre 10 y 120 años.")
        if sexo_val is not None and sexo_val not in {"M", "F", "OTRO"}:
            raise ValueError("El sexo debe ser 'M', 'F' u 'OTRO'.")

        snapshot = None
        if altura_val is not None and edad_val is not None:
            # Los cuatro predictores del CSV están disponibles: regresión lineal múltiple.
            beta = self.modelo.coeficientes()
            snapshot = json.dumps(self.modelo.snapshot(), ensure_ascii=False)
            calorias, metodo, _desglose = self._calcular_regresion(
                peso=peso,
                altura=altura_val,
                edad=edad_val,
                dur=dur,
                beta=beta,
                met=met_val,
            )
        else:
            # Respaldo para registros sin altura o sin edad (histórico/perfil incompleto).
            calorias, metodo, _desglose = self._calcular(
                peso=peso,
                dur=dur,
                met=met_val,
                fc=fc_val,
                edad=edad_val,
                sexo=sexo_val,
            )

        item = Willys_IA_CaloriaModel(
            id=0,
            usuario_id=usuario_id,
            tipo_actividad=tipo,
            peso_kg=peso,
            duracion_min=dur,
            met=met_val,
            fc_promedio=fc_val,
            edad=edad_val,
            sexo=sexo_val,
            altura_cm=altura_val,
            modelo_snapshot=snapshot,
            metodo_calculo=metodo,
            calorias_estimadas=round(calorias, 2),
        )

        if not item.validar():
            raise ValueError(
                "Datos inválidos: actividad (>=3 chars), peso, duración y MET deben ser mayores a 0."
            )

        return self._repo.guardar(item)

    def desglose_calculo(self, item: Willys_IA_CaloriaModel) -> dict:
        """
        Reconstruye la explicación del cálculo a partir de los parámetros persistidos.

        El resultado mostrado es el guardado en la predicción; la fórmula y la
        sustitución se regeneran con el mismo método usado al crear el registro.
        """
        if (item.metodo_calculo or "").upper() == "REGRESION":
            beta, snapshot_usado = self._beta_de_snapshot(item)
            altura = item.altura_cm
            if altura is None:
                raise ValueError("El registro de regresión no guardó la altura usada.")
            _calorias, _metodo, desglose = self._calcular_regresion(
                peso=float(item.peso_kg),
                altura=float(altura),
                edad=float(item.edad),
                dur=float(item.duracion_min),
                beta=beta,
                met=float(item.met),
                snapshot_usado=snapshot_usado,
            )
        else:
            _calorias, _metodo, desglose = self._calcular(
                peso=float(item.peso_kg),
                dur=float(item.duracion_min),
                met=float(item.met),
                fc=self._opcional_float(item.fc_promedio),
                edad=self._opcional_int(item.edad),
                sexo=self._normalizar_sexo(item.sexo),
                metodo_forzado=(item.metodo_calculo or "MET").upper(),
            )
        # El resultado mostrado siempre es el que quedó guardado en la predicción.
        desglose["resultado"] = round(float(item.calorias_estimadas), 2)
        return desglose

    def _beta_de_snapshot(self, item: Willys_IA_CaloriaModel) -> Tuple[List[float], bool]:
        """Recupera los β exactos del registro; si no hay snapshot usa los actuales."""
        crudo = item.modelo_snapshot
        if crudo:
            try:
                datos = json.loads(crudo)
                beta = datos.get("beta") if isinstance(datos, dict) else None
                if beta and len(beta) == 5:
                    return [float(v) for v in beta], True
            except (TypeError, ValueError):
                pass
        return self.modelo.coeficientes(), False

    def serializar(self, item: Willys_IA_CaloriaModel) -> dict:
        """Serializa una predicción añadiendo el desglose explicable (`desglose`)."""
        datos = item.to_dict()
        datos["desglose"] = self.desglose_calculo(item)
        return datos

    def obtener_registro(
        self, usuario_id: int, registro_id: int, incluir_eliminados: bool = False
    ) -> Optional[Willys_IA_CaloriaModel]:
        """Obtiene un registro propio (de la papelera solo si se solicita)."""
        try:
            uid, rid = int(usuario_id), int(registro_id)
        except (TypeError, ValueError):
            return None
        if uid <= 0 or rid <= 0:
            return None
        return self._repo.obtener_por_id(uid, rid, incluir_eliminados)

    def eliminar_registro(self, usuario_id: int, registro_id: int) -> bool:
        """Mueve un registro propio a la papelera (eliminación suave)."""
        try:
            uid, rid = int(usuario_id), int(registro_id)
        except (TypeError, ValueError):
            raise ValueError("El identificador del registro no es válido.")
        if uid <= 0 or rid <= 0:
            return False
        return self._repo.eliminar(uid, rid)

    def restaurar_registro(self, usuario_id: int, registro_id: int) -> bool:
        """Restaura un registro propio desde la papelera al historial activo."""
        try:
            uid, rid = int(usuario_id), int(registro_id)
        except (TypeError, ValueError):
            raise ValueError("El identificador del registro no es válido.")
        if uid <= 0 or rid <= 0:
            return False
        return self._repo.restaurar(uid, rid)

    def eliminar_definitivamente(self, usuario_id: int, registro_id: int) -> bool:
        """Borra de SQLite un registro propio que ya está en la papelera."""
        try:
            uid, rid = int(usuario_id), int(registro_id)
        except (TypeError, ValueError):
            raise ValueError("El identificador del registro no es válido.")
        if uid <= 0 or rid <= 0:
            return False
        return self._repo.eliminar_definitivamente(uid, rid)

    def vaciar_papelera(self, usuario_id: int) -> int:
        """Elimina definitivamente todos los registros en papelera del usuario."""
        return self._repo.vaciar_papelera(int(usuario_id))

    def listar_por_usuario(
        self, usuario_id: int, q: Optional[str] = None, actividad: Optional[str] = None
    ) -> List[Willys_IA_CaloriaModel]:
        items = self._repo.listar_por_usuario(usuario_id)
        if q:
            qn = q.strip().lower()
            items = [i for i in items if qn in (i.tipo_actividad or "").lower()]
        if actividad:
            an = actividad.strip().lower()
            items = [i for i in items if an in (i.tipo_actividad or "").lower()]
        return items

    def _paginar(
        self,
        usuario_id: int,
        q: Optional[str],
        actividad: Optional[str],
        page,
        per_page,
        solo_activos: bool,
    ) -> Dict[str, object]:
        """Paginación compartida entre historial activo y papelera."""
        try:
            pagina = int(page)
        except (TypeError, ValueError):
            pagina = 1
        try:
            por_pagina = int(per_page)
        except (TypeError, ValueError):
            por_pagina = 20

        pagina = max(1, pagina)
        por_pagina = min(100, max(1, por_pagina))

        total = self._repo.contar_por_usuario(
            usuario_id, q=q, actividad=actividad, solo_activos=solo_activos
        )
        total_paginas = math.ceil(total / por_pagina) if total else 0
        if total_paginas and pagina > total_paginas:
            pagina = total_paginas
        offset = (pagina - 1) * por_pagina

        if solo_activos:
            items = self._repo.listar_por_usuario_paginado(
                usuario_id, q=q, actividad=actividad, offset=offset, limit=por_pagina
            )
        else:
            items = self._repo.listar_papelera_paginado(
                usuario_id, q=q, actividad=actividad, offset=offset, limit=por_pagina
            )

        return {
            "items": items,
            "total": total,
            "page": pagina,
            "per_page": por_pagina,
            "total_pages": total_paginas,
            "total_calorias": self._repo.sumar_calorias_por_usuario(
                usuario_id, q=q, actividad=actividad, solo_activos=solo_activos
            ),
        }

    def listar_paginado(
        self,
        usuario_id: int,
        q: Optional[str] = None,
        actividad: Optional[str] = None,
        page=1,
        per_page=20,
    ) -> Dict[str, object]:
        """
        Retorna una página del historial activo (más reciente primero) y sus totales.

        - `page` se normaliza a >= 1; si supera el total, se ajusta a la última página.
        - `per_page` se limita a 1..100 para evitar consultas costosas.
        - `total_calorias` suma todos los registros filtrados, no solo la página.
        - Los registros en papelera quedan excluidos.
        """
        return self._paginar(usuario_id, q, actividad, page, per_page, solo_activos=True)

    def listar_papelera_paginado(
        self,
        usuario_id: int,
        q: Optional[str] = None,
        actividad: Optional[str] = None,
        page=1,
        per_page=20,
    ) -> Dict[str, object]:
        """Página de la papelera, con el mismo contrato que el historial activo."""
        return self._paginar(usuario_id, q, actividad, page, per_page, solo_activos=False)

    def exportar_csv(
        self, usuario_id: int, q: Optional[str] = None, actividad: Optional[str] = None
    ) -> str:
        """Genera el historial del usuario en CSV (con filtros opcionales)."""
        items = self.listar_por_usuario(usuario_id, q=q, actividad=actividad)
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerow([
            "Fecha", "Actividad", "Peso (kg)", "Duración (min)", "MET",
            "FC promedio (ppm)", "Edad", "Sexo", "Método", "Calorías (kcal)",
        ])
        for it in items:
            writer.writerow([
                it.fecha_registro,
                it.tipo_actividad,
                it.peso_kg,
                it.duracion_min,
                it.met,
                it.fc_promedio if it.fc_promedio is not None else "",
                it.edad if it.edad is not None else "",
                it.sexo or "",
                it.metodo_calculo,
                it.calorias_estimadas,
            ])
        return buffer.getvalue()
