"""Data center IT load + cooling (spec §2.2.11)."""
from __future__ import annotations

import math
from typing import Any

from backend.components.base import ComponentModel
from backend.configuration import get


WORKLOAD_FLEXIBILITY = {
    "llm_inference": 0.05,
    "training": 0.80,
    "batch_hpc": 0.95,
    "agentic": 0.30,
    "web_serving": 0.10,
}


class DataCenter(ComponentModel):
    component_type = "data_center"
    config_prefix = "data_center"

    def __init__(self, component_id: str = "data_center", config: dict[str, Any] | None = None) -> None:
        super().__init__(component_id, config)
        self.it_avg = float(get("data_center.it_avg_kw")) * 1000.0
        self.it_peak = float(get("data_center.it_peak_kw")) * 1000.0
        self.pue = float(get("data_center.pue"))
        self.cool = self.it_avg * (self.pue - 1.0)
        self.T_inlet = 22.0
        self.T_return = 28.0
        self.state = self._snap(self.it_avg, {"web_serving": 1.0})

    def _snap(self, P_IT: float, mix: dict[str, float]) -> dict[str, Any]:
        flex = sum(WORKLOAD_FLEXIBILITY.get(k, 0.0) * float(v) for k, v in mix.items())
        return {"P_IT": P_IT, "P_cool": self.cool, "P_total": P_IT + self.cool,
                "T_inlet": self.T_inlet, "T_return": self.T_return,
                "PUE": self.pue, "workload_mix": mix, "flexibility": flex}

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        hour = int(inputs.get("hour", 12))
        if "IT_load_W" in inputs:
            P_IT = float(inputs["IT_load_W"])
        else:
            P_IT = self.it_avg + 500.0 * math.sin((hour - 14) / 24.0 * 2.0 * math.pi)
        P_IT = max(200.0, min(self.it_peak, P_IT))
        T_amb = float(inputs.get("ambient_temp_C", 24.0))
        mix = inputs.get("workload_mix", {"web_serving": 0.4, "agentic": 0.2,
                                           "training": 0.2, "llm_inference": 0.1, "batch_hpc": 0.1})
        target_cool = (self.pue - 1.0) * P_IT
        # ASHRAE envelope: ramp cooling first if inlet would exceed envelope
        alpha = min(1.0, dt / 180.0)
        self.cool = self.cool + alpha * (target_cool - self.cool)
        # Inlet temp model: CRAC holds 22°C setpoint; rises if ambient too hot to reject
        cool_deficit = max(0.0, target_cool - self.cool)
        ambient_excess = max(0.0, T_amb - 30.0)
        self.T_inlet = 22.0 + 0.5 * ambient_excess + 0.0015 * cool_deficit + 0.0003 * (P_IT - self.it_avg)
        self.T_return = self.T_inlet + 6.0
        self.faults = ["ashrae_violation"] if not (18.0 <= self.T_inlet <= 27.0) else []
        self.state = self._snap(P_IT, dict(mix))
        return self.get_state()

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        return {41000: ("P_total", "uint16", 1.0, "W"),
                41001: ("T_inlet", "uint16", 0.1, "C"),
                41002: ("T_return", "uint16", 0.1, "C")}
