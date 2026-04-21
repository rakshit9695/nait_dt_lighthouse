"""Keysight N8937APV PV Simulator (spec §2.2.1)."""
from __future__ import annotations

import math
from typing import Any

from scipy.optimize import brentq

from backend.components.base import ComponentModel
from backend.configuration import get


class PVSimulator(ComponentModel):
    component_type = "pv_sim"
    config_prefix = "pv_sim"

    def __init__(self, component_id: str = "pv_sim", config: dict[str, Any] | None = None) -> None:
        super().__init__(component_id, config)
        self.voc_ref = float(get("pv_sim.voc_ref_v"))
        self.vmp_ref = float(get("pv_sim.vmp_ref_v"))
        self.isc_ref = float(get("pv_sim.isc_ref_a"))
        self.imp_ref = float(get("pv_sim.imp_ref_a"))
        self.p_rated = float(get("pv_sim.rated_power_w"))
        self.n = float(get("pv_sim.diode_ideality"))
        self.rs = float(get("pv_sim.series_resistance_ohm"))
        self.i0 = 1e-9
        self.state = {"P_dc": 0.0, "V_dc": self.vmp_ref, "I_dc": 0.0, "T_cell": 25.0,
                      "irradiance_W_m2": 0.0, "iterations": 0}

    def _solve_current(self, V: float, G: float, T: float) -> tuple[float, int]:
        Gn = max(G, 1.0) / 1000.0
        I_sc = self.isc_ref * Gn * (1.0 + 0.0005 * (T - 25.0))
        V_oc = self.voc_ref * (1.0 + (-0.0030) * (T - 25.0)) + 0.06 * math.log(max(Gn, 1e-4))
        Vt = self.n * 0.02585 * (T + 273.15) / 298.15
        iters = [0]

        def f(I: float) -> float:
            iters[0] += 1
            arg = min((V + I * self.rs) / max(Vt, 1e-6), 60.0)
            return I - (I_sc - self.i0 * (math.exp(arg) - 1.0))

        if V >= V_oc:
            return 0.0, iters[0]
        try:
            I = brentq(f, 0.0, max(I_sc * 1.05, 0.1), xtol=1e-4, maxiter=80)
        except ValueError:
            I = max(0.0, I_sc * (1.0 - V / max(V_oc, 1.0)))
        return max(0.0, min(I, 30.0)), iters[0]

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        G = float(inputs.get("irradiance_W_m2", 0.0))
        T = float(inputs.get("cell_temp_C", inputs.get("ambient_temp_C", 25.0)))
        V = min(max(float(inputs.get("V_dc_command", self.vmp_ref)), 0.0), 1500.0)
        I, iters = self._solve_current(V, G, T)
        P = min(V * I, self.p_rated)
        if V > 0 and P > 0:
            I = P / V
        self.state = {"P_dc": P, "V_dc": V, "I_dc": I, "T_cell": T,
                      "irradiance_W_m2": G, "iterations": iters}
        return self.get_state()

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        return {40001: ("V_dc", "uint16", 0.1, "V"),
                40002: ("I_dc", "uint16", 0.01, "A"),
                40003: ("P_dc", "uint16", 1.0, "W")}

    def reference_curves(self) -> dict[str, Any]:
        out = {"stc": {"V_oc": self.voc_ref, "V_mp": self.vmp_ref,
                        "I_sc": self.isc_ref, "I_mp": self.imp_ref}, "iv_family": []}
        for G in (200, 500, 800, 1000):
            curve = []
            for V in range(0, int(self.voc_ref) + 1, 30):
                I, _ = self._solve_current(float(V), float(G), 25.0)
                curve.append({"V": V, "I": round(I, 3), "P": round(V * I, 1)})
            out["iv_family"].append({"G": G, "curve": curve})
        return out
