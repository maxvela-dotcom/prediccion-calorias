# -*- coding: utf-8 -*-
"""
Capa de Lógica de Negocio y Reglas del Dominio (Service Layer).
Willys_IA: Patrón de Servicio.
Aplica rigurosamente las reglas inviolables de docs/SPEC.md antes de delegar al repositorio.
"""

from typing import List, Optional, Dict
from modulos.gestion_mvp.mvp_model import Willys_IA_ItemModel
from modulos.gestion_mvp.mvp_repository import Willys_IA_ItemRepository


class Willys_IA_ItemService:
    """
    Willys_IA: Orquestador de la lógica del Producto Mínimo Viable.
    Aplica las reglas de validación (RN-01 a RN-04) y se comunica con el repositorio.
    """

    def __init__(self, repositorio: Optional[Willys_IA_ItemRepository] = None):
        """
        Inyecta la dependencia del repositorio (Inversión de Control básica).
        """
        self._repo = repositorio if repositorio is not None else Willys_IA_ItemRepository()

    def registrar_elemento(self, nombre: str, categoria: str, valor: float) -> Willys_IA_ItemModel:
        """
        Willys_IA: Registra un nuevo elemento aplicando las reglas de negocio del SPEC.md.
        
        Reglas de Validación:
        - RN-01: Nombre no vacío (mínimo 3 caracteres).
        - RN-02: Valor numérico >= 0.0 (no se permiten números negativos).
        - RN-03: No se permiten duplicados del mismo nombre en estado activo.
        
        Lanza ValueError si se viola alguna regla; retorna la entidad guardada en caso exitoso.
        """
        nombre_limpio = (nombre or "").strip()
        categoria_limpia = (categoria or "General").strip()

        # Instanciar modelo preliminar para validar RN-01 y RN-02
        nuevo_item = Willys_IA_ItemModel(
            id=0,
            nombre=nombre_limpio,
            categoria_rubro=categoria_limpia,
            valor_numerico=valor,
            estado="ACTIVO"
        )

        if not nuevo_item.validar():
            raise ValueError("Datos inválidos: el nombre debe tener al menos 3 caracteres y el valor debe ser >= 0.")

        # Validación RN-03: Prevención de duplicados activos en el repositorio
        existente = self._repo.obtener_por_nombre_activo(nombre_limpio)
        if existente:
            raise ValueError(f"Registro duplicado: ya existe un elemento activo con el nombre '{nombre_limpio}'.")

        # Persistir a través del repositorio
        return self._repo.guardar(nuevo_item)

    def listar_elementos(self, filtro_estado: Optional[str] = None) -> List[Willys_IA_ItemModel]:
        """
        Willys_IA: Retorna la lista de elementos, con opción de filtro por estado.
        """
        todos = self._repo.obtener_todos()
        if filtro_estado:
            return [it for it in todos if it.estado.upper() == filtro_estado.strip().upper()]
        return todos

    def cambiar_estado(self, id_elemento: int, nuevo_estado: str) -> bool:
        """
        Willys_IA: Valida la transición de estado y delega al repositorio.
        """
        nuevo_estado_limpio = (nuevo_estado or "").strip().upper()
        item = self._repo.obtener_por_id(id_elemento)
        if not item:
            raise ValueError(f"No se encontró ningún elemento con ID #{id_elemento}.")

        # RN-04: Transición de estados válida
        estados_permitidos = {"ACTIVO", "PENDIENTE", "EN_PROCESO", "ENTREGADO", "COMPLETADO", "CANCELADO"}
        if nuevo_estado_limpio not in estados_permitidos:
            raise ValueError(f"Estado '{nuevo_estado_limpio}' no reconocido por el sistema.")

        return self._repo.actualizar_estado(id_elemento, nuevo_estado_limpio)

    def calcular_total_valores(self) -> float:
        """
        Willys_IA: Calcula la suma de todos los valores numéricos registrados.
        """
        return sum(it.valor_numerico for it in self._repo.obtener_todos())

    def obtener_resumen_metricas(self) -> Dict[str, int]:
        """
        Willys_IA: Retorna el conteo de registros agrupados por estado.
        """
        resumen: Dict[str, int] = {}
        for it in self._repo.obtener_todos():
            resumen[it.estado] = resumen.get(it.estado, 0) + 1
        return resumen

