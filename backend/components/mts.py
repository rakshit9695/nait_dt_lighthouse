"""Manual transfer switch (spec §2.2.8)."""
from __future__ import annotations

from typing import Any

from backend.components.base import ComponentModel
from backend.configuration import get


class ManualTransferSwitch(ComponentModel):
    component_type = "mts"
    config_prefix = "mts"

    def __init__(self, component_id: str = "mts", config: dict[str, Any] | None = None) -> None:
        super().__init__(component_id, config)
        self.transfer_time = float(get("mts.atg_transfer_time_s"))
        self.position = "inverter"
        self._timer = 0.0
        self.state = {"active_source": self.position, "generator_closed": False,
                      "inverter_closed": True, "transfer_time_s": self.transfer_time}

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        cmd = str(inputs.get("position_command", self.position))
        manual = bool(inputs.get("manual_override", False))
        if cmd != self.position:
            if manual:
                # manual mode: hold until override cleared
                pass
            else:
                self._timer += dt
                if self._timer >= self.transfer_time:
                    self.position = cmd
                    self._timer = 0.0
        else:
            self._timer = 0.0
        self.state = {"active_source": self.position,
                      "generator_closed": self.position == "generator",
                      "inverter_closed": self.position == "inverter",
                      "transfer_time_s": self.transfer_time}
        return self.get_state()

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        return {40700: ("active_source", "enum", 1.0, ""),
                40701: ("generator_closed", "bool", 1.0, ""),
                40702: ("inverter_closed", "bool", 1.0, "")}
