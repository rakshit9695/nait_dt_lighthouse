"""Victron Quattro 48/5000/120V bidirectional inverter (spec §2.2.4)."""
from __future__ import annotations

from typing import Any, Literal

from backend.components.base import ComponentModel
from backend.configuration import get


Mode = Literal["grid-tied", "off-grid", "assist", "passthrough"]


class VictronQuattro(ComponentModel):
    component_type = "bidir_inverter"
    config_prefix = "inverter"

    def __init__(self, component_id: str = "quattro", config: dict[str, Any] | None = None) -> None:
        super().__init__(component_id, config)
        self.p_rated = float(get("inverter.quattro_rated_power_w"))
        self.k_v = 0.5
        self.k_f = 0.02
        self.no_load_w = 25.0
        self.mode: Mode = "grid-tied"
        self._last_mode_switch = 0.0
        self.state = {"P_ac": 0.0, "P_dc": -self.no_load_w, "mode": self.mode,
                      "V_ac_out": 120.0, "f_out": 60.0, "efficiency": 0.0}

    def _eta(self, frac: float) -> float:
        f = max(0.0, min(1.0, frac))
        e = 0.82 + 0.12 * (f ** 0.3) - 0.02 * (f ** 2)
        return max(0.82, min(0.94, e))

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        # Convention: P_ac_setpoint > 0 = charge (AC->DC), < 0 = discharge (DC->AC)
        cmd = float(inputs.get("P_ac_setpoint", 0.0))
        new_mode: Mode = inputs.get("mode", self.mode)
        v_grid = float(inputs.get("V_ac_grid", 120.0))
        f_grid = float(inputs.get("f_grid", 60.0))

        if new_mode != self.mode:
            self._last_mode_switch = 0.02  # 20 ms switch time
            self.mode = new_mode
        else:
            self._last_mode_switch = max(0.0, self._last_mode_switch - dt)

        p_mag = min(abs(cmd), self.p_rated)
        eta = self._eta(p_mag / self.p_rated if self.p_rated > 0 else 0.0)
        if cmd > 0:  # charging battery
            p_ac = +p_mag
            p_dc = -p_mag * eta  # battery sees negative (charging into it: from bus' view P_dc<0)
        elif cmd < 0:  # discharging
            p_ac = -p_mag
            p_dc = +p_mag / eta
        else:
            p_ac = 0.0
            p_dc = -self.no_load_w
            eta = 0.0

        if self.mode == "off-grid":
            v_out = 120.0 - self.k_v * (p_ac / 1000.0)
            f_out = 60.0 - self.k_f * (p_ac / 1000.0)
        elif self.mode == "passthrough":
            v_out, f_out = v_grid, f_grid
            p_ac = 0.0
            p_dc = -self.no_load_w
        else:
            v_out, f_out = v_grid, f_grid

        self.state = {"P_ac": p_ac, "P_dc": p_dc, "mode": self.mode,
                      "V_ac_out": v_out, "f_out": f_out, "efficiency": eta}
        return self.get_state()

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        return {40300: ("P_ac", "int16", 1.0, "W"),
                40301: ("mode", "enum", 1.0, ""),
                40302: ("V_ac_out", "uint16", 0.1, "V"),
                40303: ("f_out", "uint16", 0.01, "Hz")}

    def reference_curves(self) -> dict[str, Any]:
        return {"peak_efficiency": 0.94, "no_load_w": 25.0,
                "droop": {"k_V_perkW": self.k_v, "k_f_perkW": self.k_f}}
