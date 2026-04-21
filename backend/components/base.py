"""Base class for component physics models (spec §2.2)."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from backend.configuration import assumptions_for
from backend.contracts import ComponentState, ComponentType


class ComponentModel:
    component_type: ComponentType = "panel"  # overridden
    config_prefix: str = ""

    def __init__(self, component_id: str, config: dict[str, Any] | None = None) -> None:
        self.component_id = component_id
        self.config = config or {}
        self.state: dict[str, Any] = {}
        self.faults: list[str] = []
        self.assumptions = assumptions_for(self.config_prefix or component_id)

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def get_state(self) -> dict[str, Any]:
        return deepcopy(self.state)

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        return {}

    def reference_curves(self) -> dict[str, Any]:
        return {}

    def snapshot(self, ts: datetime | None = None) -> ComponentState:
        return ComponentState(
            component_id=self.component_id,
            type=self.component_type,
            timestamp=ts or datetime.now(timezone.utc),
            state=self.get_state(),
            assumptions=self.assumptions,
            faults=list(self.faults),
        )
