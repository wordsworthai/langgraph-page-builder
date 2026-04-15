# immutable_store.py
from __future__ import annotations
from typing import Dict, Optional
from template_json_builder.autopopulation.autopopulators.graph_state import AutopopulationImmutableState


class ImmutableStore:
    """Abstract-ish interface; swap this for Redis/S3 later."""
    async def put(self, run_id: str, value: AutopopulationImmutableState) -> None:
        raise NotImplementedError
    async def get(self, run_id: str) -> Optional[AutopopulationImmutableState]:
        raise NotImplementedError
    async def delete(self, run_id: str) -> None:
        raise NotImplementedError


class InProcImmutableStore(ImmutableStore):
    def __init__(self) -> None:
        self._data: Dict[str, AutopopulationImmutableState] = {}

    async def put(self, run_id: str, value: AutopopulationImmutableState) -> None:
        self._data[run_id] = value.model_copy(deep=True)

    async def get(self, run_id: str) -> Optional[AutopopulationImmutableState]:
        v = self._data.get(run_id)
        return v.model_copy(deep=True) if v else None

    async def delete(self, run_id: str) -> None:
        self._data.pop(run_id, None)


immutable_store = InProcImmutableStore()
