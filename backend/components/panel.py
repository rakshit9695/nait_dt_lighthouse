"""240/120V split-phase panel with three branch breakers (spec §2.2.9)."""
from __future__ import annotations

from typing import Any

from backend.components.base import ComponentModel
from backend.configuration import get


BRANCHES = ("data_center", "grid_branch", "pv_branch")


class SplitPhasePanel(ComponentModel):
    component_type = "panel"
    config_prefix = "panel"

    def __init__(self, component_id: str = "panel", config: dict[str, Any] | None = None) -> None:
        super().__init__(component_id, config)
        self.i_trip = float(get("panel.branch_trip_a"))
        self.accum: dict[str, float] = {b: 0.0 for b in BRANCHES}
        self.positions: dict[str, str] = {b: "closed" for b in BRANCHES}
        self.state = {"voltage_v": 240.0, "branch_currents_a": {b: 0.0 for b in BRANCHES},
                      "branch_positions": dict(self.positions), "trip_flags": []}

    def _trip_time(self, I: float) -> float:
        if I <= self.i_trip:
            return float("inf")
        denom = (I / self.i_trip) ** 2 - 1.0
        return max(0.02, min(60.0, 0.18 / max(denom, 1e-9)))

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        V = float(inputs.get("voltage_v", 240.0))
        powers = inputs.get("branch_powers_w", {}) or {}
        currents: dict[str, float] = {}
        trip_now: list[str] = []
        for b in BRANCHES:
            P = abs(float(powers.get(b, 0.0)))
            I = P / max(V, 1.0)
            currents[b] = I
            if self.positions[b] == "tripped":
                trip_now.append(b)
                continue
            if I > self.i_trip:
                self.accum[b] += dt
                if self.accum[b] >= self._trip_time(I):
                    self.positions[b] = "tripped"
                    trip_now.append(b)
            else:
                self.accum[b] = 0.0
        self.faults = list(trip_now)
        self.state = {"voltage_v": V, "branch_currents_a": currents,
                      "branch_positions": dict(self.positions), "trip_flags": trip_now,
                      "i_trip_a": self.i_trip}
        return self.get_state()

    def reset_breaker(self, branch: str) -> None:
        if branch in self.positions:
            self.positions[branch] = "closed"
            self.accum[branch] = 0.0

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        return {40800: ("voltage_v", "uint16", 0.1, "V"),
                40801: ("trip_flags", "bitmap", 1.0, "")}
