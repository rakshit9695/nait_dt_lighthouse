"""Fronius Primo 3.8-1 Inverter (spec §2.2.2)."""
from __future__ import annotations

from typing import Any

import numpy as np

from backend.components.base import ComponentModel
from backend.configuration import get


CEC_PTS = np.array([
    [0.10, 0.938], [0.20, 0.966], [0.30, 0.971],
    [0.50, 0.972], [0.75, 0.971], [1.00, 0.968],
])


class FroniusPrimo(ComponentModel):
    component_type = "inverter"
    config_prefix = "inverter"

    def __init__(self, component_id: str = "fronius", config: dict[str, Any] | None = None) -> None:
        super().__init__(component_id, config)
        self.p_rated = float(get("inverter.fronius_rated_power_w"))
        self.v_dc_request = 720.0
        self.v_trip_t = 0.0
        self.f_trip_t = 0.0
        self.status = "online"
        self._mpp_dir = +1
        self._mpp_step = 5.0
        self._last_p = 0.0
        self.state = {"P_ac": 0.0, "Q_ac": 0.0, "V_dc_request": self.v_dc_request,
                      "efficiency": 0.0, "status": "online"}

    def _eta(self, frac: float) -> float:
        return float(np.interp(max(0.0, min(frac, 1.0)), CEC_PTS[:, 0], CEC_PTS[:, 1]))

    def _mppt(self, p_now: float) -> None:
        if p_now > self._last_p:
            self.v_dc_request += self._mpp_dir * self._mpp_step
        else:
            self._mpp_dir *= -1
            self.v_dc_request += self._mpp_dir * self._mpp_step
        self.v_dc_request = max(500.0, min(900.0, self.v_dc_request))
        self._last_p = p_now

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        p_dc = float(inputs.get("P_dc_available", 0.0))
        v_grid = float(inputs.get("V_grid_ac", 240.0))
        f_grid = float(inputs.get("f_grid", 60.0))
        sp = float(inputs.get("P_ac_setpoint", 1.0))

        self.v_trip_t = self.v_trip_t + dt if abs(v_grid - 240.0) > 24.0 else 0.0
        self.f_trip_t = self.f_trip_t + dt if abs(f_grid - 60.0) > 0.5 else 0.0
        if self.v_trip_t > 1.0 or self.f_trip_t > 0.16:
            self.status = "tripped"
            self.state.update({"P_ac": 0.0, "Q_ac": 0.0, "efficiency": 0.0,
                               "V_dc_request": self.v_dc_request, "status": "tripped"})
            self.faults = ["ride_through_trip"]
            return self.get_state()

        self.faults = []
        self.status = "online"
        self._mppt(p_dc)
        eta = self._eta(p_dc / self.p_rated if self.p_rated > 0 else 0.0)
        p_ac = min(p_dc * eta, self.p_rated, max(0.0, sp) * self.p_rated)
        self.state = {"P_ac": p_ac, "Q_ac": 0.0, "V_dc_request": self.v_dc_request,
                      "efficiency": eta, "status": "online"}
        return self.get_state()

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        # SunSpec inverter model 101 abridged
        return {40069: ("AC_Power", "uint16", 1.0, "W"),
                40083: ("DC_Voltage_request", "uint16", 0.1, "V"),
                40087: ("Status", "enum", 1.0, "")}

    def reference_curves(self) -> dict[str, Any]:
        return {"weighted_cec_efficiency": 0.966, "curve": CEC_PTS.tolist()}
