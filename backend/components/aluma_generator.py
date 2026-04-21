"""AlumaPower aluminum-air generator (spec §2.2.7)."""
from __future__ import annotations

import math
from typing import Any

from backend.components.base import ComponentModel
from backend.configuration import get


class AlumaPowerGenerator(ComponentModel):
    component_type = "generator"
    config_prefix = "generator"

    V_OC = 54.0
    R_OHM = 0.08
    A = 1.2
    I0 = 0.5
    M = 0.02
    N = 0.05
    KWH_PER_KG = 1.2  # actual specific energy

    def __init__(self, component_id: str = "generator", config: dict[str, Any] | None = None) -> None:
        super().__init__(component_id, config)
        self.p_rated = float(get("generator.rated_power_w"))
        self.p_peak = float(get("generator.peak_power_w"))
        self.fuel_kg = float((config or {}).get("initial_fuel_kg", get("generator.fuel_tank_kg")))
        self.state_name = "off"
        self.start_t = 0.0
        self.p_out = 0.0
        self.state = {"V_dc": self.V_OC, "I_dc": 0.0, "P_dc": 0.0,
                      "fuel_kg_remaining": self.fuel_kg, "state": "off"}

    def _polarization(self, I: float) -> float:
        if I <= 0:
            return self.V_OC
        V = (self.V_OC - self.R_OHM * I
             - self.A * math.log(max(I / self.I0, 1.0))
             - self.M * math.exp(self.N * min(I, 80.0)))
        return max(20.0, min(self.V_OC, V))

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        enable = bool(inputs.get("enable", False))
        p_req = max(0.0, min(float(inputs.get("P_request_W", 0.0)), self.p_peak))

        if not enable or self.fuel_kg <= 0.0:
            self.state_name = "off"
            self.start_t = 0.0
            self.p_out = max(0.0, self.p_out - 400.0 * dt)
        elif self.state_name in ("off", "starting") and self.start_t + dt < 30.0:
            self.state_name = "starting"
            self.start_t += dt
            self.p_out = 0.0
        else:
            # Either already running, or dt covers startup
            running_dt = dt if self.state_name == "running" else max(dt - max(0.0, 30.0 - self.start_t), 0.0)
            self.state_name = "running"
            self.start_t = 30.0
            ramp = 200.0 * running_dt
            tgt = min(p_req, self.p_rated)
            if tgt > self.p_out:
                self.p_out = min(tgt, self.p_out + ramp)
            else:
                self.p_out = max(tgt, self.p_out - ramp)
            if dt >= 60.0 and tgt > 0:
                # Long timestep: assume settled to target after ramp
                self.p_out = tgt

        if self.p_out > 0:
            # solve V,I along polarization
            I = self.p_out / 48.0
            for _ in range(8):
                V = self._polarization(I)
                I = self.p_out / max(V, 1.0)
            V = self._polarization(I)
            self.p_out = V * I
        else:
            V, I = self.V_OC, 0.0

        # fuel consumption: kWh = P*dt/3600/1000; kg = kWh / kwh_per_kg
        if self.p_out > 0:
            kwh = self.p_out * dt / 3.6e6
            self.fuel_kg = max(0.0, self.fuel_kg - kwh / self.KWH_PER_KG)

        self.faults = ["fuel_empty"] if self.fuel_kg <= 0.0 else []
        self.state = {"V_dc": V, "I_dc": I, "P_dc": self.p_out,
                      "fuel_kg_remaining": self.fuel_kg, "state": self.state_name}
        return self.get_state()

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        return {40600: ("P_dc", "uint16", 1.0, "W"),
                40601: ("fuel_kg_remaining", "uint16", 0.01, "kg"),
                40602: ("state", "enum", 1.0, "")}

    def reference_curves(self) -> dict[str, Any]:
        return {"polarization": [{"I": i, "V": self._polarization(float(i))} for i in range(0, 80, 4)],
                "specific_energy_kwh_per_kg": self.KWH_PER_KG}
