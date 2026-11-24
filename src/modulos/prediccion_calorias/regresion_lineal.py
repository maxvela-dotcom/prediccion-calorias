# -*- coding: utf-8 -*-
"""
Regresión Lineal Múltiple con la ecuación normal (Willys_IA).

    β = (Xᵀ X)⁻¹ · Xᵀ · Y

El dataset de entrenamiento vive en `data/dataset_calorias.csv` y contiene
cuatro variables independientes anonimizadas:

    X_1 = peso (kg)   X_2 = altura (cm)   X_3 = edad (años)   X_4 = duración (min)
    Y   = calorías estimadas (kcal)

Toda la álgebra se hace con NumPy de forma explícita: se construye X con una
columna de unos para el intercepto, se calculan Xᵀ, XᵀX y XᵀY, se invierte
XᵀX y se obtiene β. El módulo expone además las matrices, las métricas y los
datos de las gráficas para la sección de análisis técnico del dashboard.
"""

import csv
import os
from typing import Dict, List, Optional, Sequence

import numpy as np

ARCHIVO_DATASET = "dataset_calorias.csv"
RUTA_DATASET = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", ARCHIVO_DATASET)
)

COLUMNAS_CSV = ("X_1", "X_2", "X_3", "X_4", "Y")
NOMBRES_X = [
    "β0 · unos (intercepto)",
    "X1 · peso (kg)",
    "X2 · altura (cm)",
    "X3 · edad (años)",
    "X4 · minutos",
]
SIMBOLOS_BETA = ["β0", "β1", "β2", "β3", "β4"]
VARIABLES = [
    {"simbolo": "β0", "nombre": "Intercepto", "unidad": "", "columna": "unos"},
    {"simbolo": "β1", "nombre": "peso (X1)", "unidad": "kg", "columna": "X_1"},
    {"simbolo": "β2", "nombre": "altura (X2)", "unidad": "cm", "columna": "X_2"},
    {"simbolo": "β3", "nombre": "edad (X3)", "unidad": "años", "columna": "X_3"},
    {"simbolo": "β4", "nombre": "minutos de actividad (X4)", "unidad": "min", "columna": "X_4"},
]

ECUACION_SIMBOLICA = "Ŷ = β0 + β1X1 + β2X2 + β3X3 + β4X4"
FORMULA_NORMAL = "β = (XᵀX)⁻¹ · XᵀY"
NOTA_METODO = (
    "Ecuación normal resuelta con NumPy. β se obtiene por inversión directa de XᵀX; "
    "no se usa un solver de librería de machine learning."
)


def cargar_dataset(ruta: Optional[str] = None) -> List[Dict[str, float]]:
    """Lee y valida el CSV; devuelve una fila por registro con claves X_1..X_4 e Y."""
    ruta = ruta or RUTA_DATASET
    if not os.path.isfile(ruta):
        raise ValueError(f"No se encontró el dataset de entrenamiento: {ruta}")

    filas: List[Dict[str, float]] = []
    with open(ruta, "r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        cabeceras = set(lector.fieldnames or [])
        faltantes = [c for c in COLUMNAS_CSV if c not in cabeceras]
        if faltantes:
            raise ValueError(
                "El CSV debe contener las columnas " + ", ".join(COLUMNAS_CSV)
                + ". Faltan: " + ", ".join(faltantes)
            )
        for numero, fila in enumerate(lector, start=2):
            registro = {}
            for columna in COLUMNAS_CSV:
                texto = (fila.get(columna) or "").strip()
                try:
                    registro[columna] = float(texto)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Valor numérico inválido en {columna}, fila {numero} del CSV."
                    ) from None
            filas.append(registro)

    if len(filas) < len(COLUMNAS_CSV):
        raise ValueError("El dataset necesita al menos 5 filas para ajustar el modelo.")
    return filas


def construir_matrices(filas: Sequence[Dict[str, float]]):
    """Construye X (con columna de unos) e Y como vectores columna de NumPy."""
    if not filas:
        raise ValueError("No hay filas para construir las matrices.")
    x = np.array(
        [
            [1.0, float(f["X_1"]), float(f["X_2"]), float(f["X_3"]), float(f["X_4"])]
            for f in filas
        ],
        dtype=float,
    )
    y = np.array([[float(f["Y"])] for f in filas], dtype=float)
    return x, y


def _redondear(valor, decimales: int = 4) -> float:
    return round(float(valor), decimales)


def _matriz_a_lista(matriz: np.ndarray, decimales: int = 3) -> List[List[float]]:
    return [[_redondear(v, decimales) for v in fila] for fila in np.asarray(matriz)]


def predecir_con_coeficientes(
    beta: Sequence[float], peso: float, altura: float, edad: float, minutos: float
) -> float:
    """Evalúa Ŷ = β0 + β1·peso + β2·altura + β3·edad + β4·minutos."""
    if len(beta) != 5:
        raise ValueError("El vector β debe tener 5 coeficientes (β0..β4).")
    vector = np.array([1.0, float(peso), float(altura), float(edad), float(minutos)])
    return float(np.dot(np.asarray(beta, dtype=float), vector))


class RegresionLineal:
    """Modelo entrenado una vez desde el CSV mediante la ecuación normal."""

    def __init__(self, ruta_csv: Optional[str] = None):
        self.ruta_csv = ruta_csv or RUTA_DATASET
        self.filas = cargar_dataset(self.ruta_csv)
        self.X, self.Y = construir_matrices(self.filas)

        self.XT = self.X.T
        self.XTX = self.XT @ self.X
        self.XTY = self.XT @ self.Y
        try:
            # Ecuación normal explícita, sin sklearn ni optimizadores iterativos.
            self.beta = np.linalg.inv(self.XTX) @ self.XTY
        except np.linalg.LinAlgError as err:
            raise ValueError(
                "No se puede invertir XᵀX: las variables del CSV son linealmente dependientes."
            ) from err

        self.predicciones = self.X @ self.beta
        self.residuos = self.Y - self.predicciones
        self.mae = float(np.mean(np.abs(self.residuos)))
        self.rmse = float(np.sqrt(np.mean(self.residuos ** 2)))
        suma_residuos = float(np.sum(self.residuos ** 2))
        suma_total = float(np.sum((self.Y - float(self.Y.mean())) ** 2))
        self.r2 = 1.0 - suma_residuos / suma_total if suma_total else 0.0

    # ------------------------------------------------------------------
    # Uso del modelo
    # ------------------------------------------------------------------

    def coeficientes(self) -> List[float]:
        return [float(v) for v in self.beta.ravel()]

    def predecir(self, peso: float, altura: float, edad: float, minutos: float) -> float:
        return predecir_con_coeficientes(
            self.coeficientes(), peso, altura, edad, minutos
        )

    def snapshot(self) -> dict:
        """Copia mínima de β para reconstruir cálculos históricos aunque cambie el CSV."""
        return {
            "version": 1,
            "fuente": os.path.basename(self.ruta_csv),
            "metodo": "REGRESION",
            "beta": [round(b, 6) for b in self.coeficientes()],
        }

    def ecuacion_numerica(self, beta: Optional[Sequence[float]] = None) -> str:
        b = list(beta) if beta is not None else self.coeficientes()
        return (
            f"Ŷ = {_redondear(b[0])} + {_redondear(b[1])}·X1 "
            f"+ {_redondear(b[2])}·X2 + {_redondear(b[3])}·X3 "
            f"+ {_redondear(b[4])}·X4"
        )

    def interpretacion(self) -> List[dict]:
        b = self.coeficientes()
        resultado = []
        for i, info in enumerate(VARIABLES):
            valor = _redondear(b[i])
            if i == 0:
                texto = (
                    f"β0 = {valor} kcal es el valor base de la ecuación cuando "
                    "X1, X2, X3 y X4 valen 0; es una referencia matemática, no una rutina real."
                )
            else:
                verbo = "aumentan" if valor >= 0 else "disminuyen"
                texto = (
                    f"Por cada {info['unidad']} adicional de {info['nombre']} ({info['simbolo']}), "
                    f"las calorías {verbo} {abs(valor)} kcal, manteniendo constantes las demás variables."
                )
            resultado.append(
                {
                    "simbolo": info["simbolo"],
                    "variable": info["nombre"],
                    "unidad": info["unidad"],
                    "coeficiente": valor,
                    "texto": texto,
                }
            )
        return resultado

    # ------------------------------------------------------------------
    # Serialización para el dashboard
    # ------------------------------------------------------------------

    def serializar(self) -> dict:
        beta = self.coeficientes()
        filas_tabla = [
            {
                "X_1": _redondear(f["X_1"], 2),
                "X_2": _redondear(f["X_2"], 2),
                "X_3": _redondear(f["X_3"], 2),
                "X_4": _redondear(f["X_4"], 2),
                "Y": _redondear(f["Y"], 2),
            }
            for f in self.filas
        ]

        estadisticas = []
        for columna in COLUMNAS_CSV:
            valores = np.array([f[columna] for f in self.filas], dtype=float)
            estadisticas.append(
                {
                    "columna": columna,
                    "media": _redondear(valores.mean(), 2),
                    "mediana": _redondear(np.median(valores), 2),
                    "minimo": _redondear(valores.min(), 2),
                    "maximo": _redondear(valores.max(), 2),
                    "desviacion": _redondear(valores.std(ddof=1), 2),
                }
            )

        n = int(self.X.shape[0])
        return {
            "dataset": {
                "archivo": ARCHIVO_DATASET,
                "ruta": "data/" + ARCHIVO_DATASET,
                "filas": n,
                "columnas": list(COLUMNAS_CSV),
                "columnas_descripcion": [
                    "X_1 peso (kg)", "X_2 altura (cm)", "X_3 edad (años)",
                    "X_4 minutos de actividad", "Y calorías (kcal)",
                ],
                "vista_previa": filas_tabla[:8],
                "estadisticas": estadisticas,
                "nota": "Datos ficticios y anonimizados generados para la práctica; no son registros personales.",
            },
            "matrices": {
                "X": {
                    "dimensiones": [n, 5],
                    "columnas": NOMBRES_X,
                    "vista_previa": _matriz_a_lista(self.X[:6], 2),
                    "nota": "La primera columna de unos permite estimar el intercepto β0.",
                },
                "XT": {
                    "dimensiones": [5, n],
                    "vista_previa": _matriz_a_lista(self.XT[:, :6], 2),
                    "nota": f"Se muestran 6 de las {n} columnas de Xᵀ por espacio.",
                },
                "Y": {
                    "dimensiones": [n, 1],
                    "vista_previa": _matriz_a_lista(self.Y[:6], 2),
                },
                "XTX": {
                    "dimensiones": [5, 5],
                    "valores": _matriz_a_lista(self.XTX, 2),
                },
                "XTY": {
                    "dimensiones": [5, 1],
                    "valores": _matriz_a_lista(self.XTY, 2),
                },
                "beta": {
                    "dimensiones": [5, 1],
                    "simbolos": SIMBOLOS_BETA,
                    "vista_previa": _matriz_a_lista(self.beta, 4),
                },
            },
            "formula_normal": FORMULA_NORMAL,
            "nota_metodo": NOTA_METODO,
            "pasos": [
                f"1. X tiene dimensión ({n}, 5): {n} observaciones y 5 columnas (unos + 4 predictores).",
                f"2. Xᵀ tiene dimensión (5, {n}); Y tiene dimensión ({n}, 1).",
                "3. XᵀX es (5, 5) y XᵀY es (5, 1).",
                "4. β = (XᵀX)⁻¹ · XᵀY da un vector (5, 1) con β0..β4.",
                f"5. Ŷ = X · β produce {n} predicciones y {n} residuos para calcular las métricas.",
            ],
            "ecuacion": ECUACION_SIMBOLICA,
            "ecuacion_numerica": self.ecuacion_numerica(beta),
            "interpretacion": self.interpretacion(),
            "metricas": {
                "MAE": _redondear(self.mae, 4),
                "RMSE": _redondear(self.rmse, 4),
                "R2": _redondear(self.r2, 4),
            },
            "graficas": {
                "real_vs_predicho": [
                    {
                        "x": _redondear(real[0], 2),
                        "y": _redondear(pred[0], 2),
                    }
                    for real, pred in zip(self.Y, self.predicciones)
                ],
                "residuos": [
                    {"x": _redondear(pred[0], 2), "y": _redondear(res[0], 2)}
                    for pred, res in zip(self.predicciones, self.residuos)
                ],
                "impacto": [
                    {
                        "variable": variable["simbolo"] + " · " + variable["nombre"],
                        "coeficiente": _redondear(beta[i], 4),
                    }
                    for i, variable in enumerate(VARIABLES)
                    if i > 0
                ],
            },
        }
