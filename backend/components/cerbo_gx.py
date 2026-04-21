"""Victron Cerbo GX system controller (spec §2.2.5)."""
from __future__ import annotations

from typing import Any

from backend.components.base import ComponentModel


class CerboGX(ComponentModel):
    component_type = "system_controller"
    config_prefix = "cerbo"

    def __init__(self, component_id: str = "cerbo", config: dict[str, Any] | None = None) -> None:
        super().__init__(component_id, config)
        self.state = {"alerts": [], "ess_mode": "auto", "minimum_soc": 0.20,
                      "aggregated": {}, "poll_count": 0}

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        bat = inputs.get("battery", {}) or {}
        grid = inputs.get("grid", {}) or {}
        quattro = inputs.get("quattro", {}) or {}
        alerts: list[str] = []
        soc = float(bat.get("SOC", 0.5))
        if soc < 0.15:
            alerts.append("low_soc")
        for f in bat.get("fault_flags", []) or []:
            alerts.append(f"battery:{f}")
        ess_mode = "support" if grid.get("online", True) else "island"
        self.state = {
            "alerts": alerts,
            "ess_mode": ess_mode,
            "minimum_soc": 0.20,
            "aggregated": {"battery_SOC": soc, "battery_T": bat.get("T", 25.0),
                           "grid_online": grid.get("online", True),
                           "quattro_mode": quattro.get("mode", "grid-tied")},
            "poll_count": int(self.state.get("poll_count", 0)) + 1,
        }
        return self.get_state()

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        return {40400: ("ess_mode", "enum", 1.0, ""),
                40401: ("minimum_soc", "uint16", 0.001, "pu")}
