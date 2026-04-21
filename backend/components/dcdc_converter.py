"""Generic 48 V buck-boost DC-DC converter (spec §2.2.6)."""
from __future__ import annotations

from typing import Any

from backend.components.base import ComponentModel
from backend.configuration import get


class DCDCConverter(ComponentModel):
    component_type = "dcdc"
    config_prefix = "dcdc"

    def __init__(self, component_id: str = "dcdc", config: dict[str, Any] | None = None) -> None:
        super().__init__(component_id, config)
        self.p_rated = float(get("dcdc.rated_power_w"))
        self.i_lim = float(get("dcdc.output_current_limit_a"))
        self.last_p = 0.0
        self.state = {"V_in": 48.0, "V_out": 48.0, "I_out": 0.0,
                      "P_in": 0.0, "P_out": 0.0, "P_loss": 0.0, "enabled": False}

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        enable = bool(inputs.get("enable", False))
        v_in = float(inputs.get("V_in", 48.0))
        p_avail = max(0.0, float(inputs.get("P_in_available_W", 0.0)))
        v_out = max(40.0, min(60.0, float(inputs.get("V_out_command", 51.2))))
        target = min(p_avail, self.p_rated) if enable else 0.0
        ramp = 500.0 * dt
        if target > self.last_p:
            p_in = min(target, self.last_p + ramp)
        else:
            p_in = max(target, self.last_p - ramp)
        # efficiency: 0.94 above 20% load, linear derate below
        thr = 0.2 * self.p_rated
        if p_in >= thr:
            eta = 0.94
        else:
            eta = 0.80 + 0.14 * (p_in / max(thr, 1.0))
        p_out = p_in * eta
        i_out = min(self.i_lim, p_out / max(v_out, 1.0))
        p_out = i_out * v_out
        self.last_p = p_in
        self.state = {"V_in": v_in, "V_out": v_out, "I_out": i_out,
                      "P_in": p_in, "P_out": p_out, "P_loss": max(p_in - p_out, 0.0),
                      "enabled": enable, "efficiency": eta}
        return self.get_state()

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        return {40500: ("P_out", "uint16", 1.0, "W"),
                40501: ("I_out", "uint16", 0.01, "A"),
                40502: ("enabled", "bool", 1.0, "")}
