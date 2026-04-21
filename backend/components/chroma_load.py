"""Chroma 61809 regenerative grid simulator / programmable load (spec §2.2.10)."""
from __future__ import annotations

from typing import Any

from backend.components.base import ComponentModel


class Chroma61809(ComponentModel):
    component_type = "load_sim"
    config_prefix = "chroma"

    def __init__(self, component_id: str = "chroma", config: dict[str, Any] | None = None) -> None:
        super().__init__(component_id, config)
        self.state = {"P": 0.0, "Q": 0.0, "V": 240.0, "f": 60.0, "mode": "load"}

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        mode = str(inputs.get("mode", "load"))
        P = float(inputs.get("P_command_W", 0.0))
        V = float(inputs.get("V_command", 240.0))
        f = float(inputs.get("f_command", 60.0))
        # Clip to spec ranges
        V = max(170.0, min(300.0, V))
        f = max(45.0, min(65.0, f))
        if mode == "load":
            P = max(0.0, min(9000.0, P))
        else:
            P = max(-9000.0, min(9000.0, P))
        self.state = {"P": P, "Q": 0.0, "V": V, "f": f, "mode": mode}
        return self.get_state()

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        return {40900: ("P", "int16", 1.0, "W"),
                40901: ("mode", "enum", 1.0, ""),
                40902: ("V", "uint16", 0.1, "V")}
