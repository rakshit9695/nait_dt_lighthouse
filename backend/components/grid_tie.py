"""Main grid tie (spec §2.2.12)."""
from __future__ import annotations

from typing import Any

from backend.components.base import ComponentModel
from backend.configuration import get


class GridTie(ComponentModel):
    component_type = "grid_tie"
    config_prefix = "grid"

    def __init__(self, component_id: str = "grid", config: dict[str, Any] | None = None) -> None:
        super().__init__(component_id, config)
        self.p_imp_max = float(get("grid.import_limit_w"))
        self.p_exp_max = float(get("grid.export_limit_w"))
        self.state = {"P_exchanged": 0.0, "LMP": 60.0, "CI_gco2_kwh": 500.0,
                      "V": 240.0, "f": 60.0, "online": True}

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        online = bool(inputs.get("online", True))
        # Convention: P_exchange_request_W > 0 = importing from grid, < 0 = exporting
        req = float(inputs.get("P_exchange_request_W", 0.0))
        if online:
            P = max(-self.p_exp_max, min(self.p_imp_max, req))
        else:
            P = 0.0
        self.faults = ["grid_outage"] if not online else []
        self.state = {"P_exchanged": P,
                      "LMP": float(inputs.get("LMP", self.state.get("LMP", 60.0))),
                      "CI_gco2_kwh": float(inputs.get("CI_gco2_kwh", self.state.get("CI_gco2_kwh", 500.0))),
                      "V": 240.0 if online else 0.0,
                      "f": 60.0 if online else 0.0,
                      "online": online,
                      "import_limit_w": self.p_imp_max,
                      "export_limit_w": self.p_exp_max}
        return self.get_state()

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        return {41100: ("P_exchanged", "int16", 1.0, "W"),
                41101: ("LMP", "uint16", 0.1, "USD/MWh"),
                41102: ("online", "bool", 1.0, "")}
