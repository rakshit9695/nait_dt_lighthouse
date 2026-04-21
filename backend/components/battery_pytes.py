"""Pytes V5 LFP battery (spec §2.2.3)."""
from __future__ import annotations

from typing import Any

from backend.components.base import ComponentModel
from backend.configuration import get


def lfp_ocv(soc: float) -> float:
    """LFP OCV-SOC piecewise curve (pack-level, ~52 V at mid-SOC)."""
    s = max(0.0, min(1.0, soc))
    if s <= 0.10:
        return 44.0 + (50.0 - 44.0) * (s / 0.10)
    if s >= 0.90:
        return 52.5 + (54.0 - 52.5) * ((s - 0.90) / 0.10)
    return 50.0 + (52.5 - 50.0) * ((s - 0.10) / 0.80)


class PytesBattery(ComponentModel):
    component_type = "battery"
    config_prefix = "battery"

    def __init__(self, component_id: str = "battery", config: dict[str, Any] | None = None) -> None:
        super().__init__(component_id, config)
        self.cap_ah = float(get("battery.capacity_ah"))
        self.v_nom = float(get("battery.nominal_voltage_v"))
        self.r0 = float(get("battery.r0_ohm"))
        self.r1 = float(get("battery.r1_ohm"))
        self.c1 = float(get("battery.c1_f"))
        self.imax = float(get("battery.max_current_a"))
        self.mcp = float(get("battery.thermal_capacity_j_per_k"))
        self.h = float(get("battery.thermal_conductance_w_per_k"))
        self.soc = float((config or {}).get("initial_soc", 0.5))
        self.v_rc = 0.0
        self.T = 25.0
        self.soh = 1.0
        self.cycles_ah = 0.0
        self._update_state(0.0, lfp_ocv(self.soc))

    def _bms_clip(self, I_req: float) -> float:
        I = max(-self.imax, min(self.imax, I_req))
        # convention: I>0 = discharge
        if self.soc <= 0.10 and I > 0:
            I = 0.0
        if self.soc >= 0.95 and I < 0:
            I = 0.0
        if self.T > 45.0:
            if I < 0:
                I = 0.0
            else:
                I *= 0.5
        return I

    def _update_state(self, I: float, V: float) -> None:
        faults: list[str] = []
        if self.T > 50.0:
            faults.append("over_temperature")
        if abs(I) >= self.imax - 1e-3:
            faults.append("over_current")
        if V < 40.0:
            faults.append("under_voltage_cutoff")
        self.faults = faults
        self.state = {"SOC": self.soc, "SOH": self.soh, "V_term": V, "I": I,
                      "P_dc": V * I, "T": self.T, "V_RC": self.v_rc,
                      "fault_flags": faults, "cycle_throughput_ah": self.cycles_ah}

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        # P>0 means discharge (delivering to bus)
        P_req = float(inputs.get("P_bat_request_W", 0.0))
        T_amb = float(inputs.get("ambient_temp_C", 25.0))
        ocv = lfp_ocv(self.soc)
        I_req = P_req / max(ocv, 1.0)
        I = self._bms_clip(I_req)
        # discharge reduces SOC
        self.soc = max(0.10, min(0.95, self.soc - I * dt / (3600.0 * self.cap_ah)))
        # 1RC dynamics — closed-form to stay stable at any dt
        tau = max(self.r1 * self.c1, 1e-6)
        v_inf = I * self.r1
        import math as _m
        decay = _m.exp(-dt / tau)
        self.v_rc = v_inf + (self.v_rc - v_inf) * decay
        V = lfp_ocv(self.soc) - I * self.r0 - self.v_rc
        # thermal — first-order: closed-form for stability
        loss = (I * I) * (self.r0 + self.r1)
        if self.mcp > 0 and self.h > 0:
            T_eq = T_amb + loss / self.h
            tau_th = self.mcp / self.h
            self.T = T_eq + (self.T - T_eq) * _m.exp(-dt / tau_th)
        # SOH
        self.cycles_ah += abs(I) * dt / 3600.0
        full_cycles = self.cycles_ah / max(2.0 * self.cap_ah, 1.0)
        self.soh = max(0.7, 1.0 - full_cycles * 1e-5)
        self._update_state(I, V)
        return self.get_state()

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        return {40200: ("SOC", "uint16", 0.001, "pu"),
                40201: ("V_term", "uint16", 0.01, "V"),
                40202: ("I", "int16", 0.01, "A"),
                40203: ("T", "int16", 0.1, "C")}

    def reference_curves(self) -> dict[str, Any]:
        return {"round_trip_efficiency": 0.95, "cycle_life_80_dod": 6000,
                "ocv_soc": [{"SOC": s / 100, "V": lfp_ocv(s / 100)} for s in range(0, 101, 5)]}
