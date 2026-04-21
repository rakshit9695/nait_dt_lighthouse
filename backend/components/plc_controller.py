"""Site PLC controller (spec §2.2.13)."""
from __future__ import annotations

from typing import Any

from backend.components.base import ComponentModel
from backend.control.policies import POLICIES


class SitePLC(ComponentModel):
    component_type = "plc"
    config_prefix = "plc"

    def __init__(self, component_id: str = "plc", config: dict[str, Any] | None = None) -> None:
        super().__init__(component_id, config)
        self.policy = str((config or {}).get("policy", "rule_baseline"))
        self.cmd_queue: list[dict[str, Any]] = []
        self.state = {"policy": self.policy, "loop_rate_hz": 1.0,
                      "commands": {}, "queue_len": 0, "decision_latency_ms": 12.0}

    def step(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        self.policy = str(inputs.get("policy", self.policy))
        handler = POLICIES[self.policy]
        cmds = handler(inputs)
        self.cmd_queue.append({"t_dt": dt, "commands": cmds})
        if len(self.cmd_queue) > 10:
            self.cmd_queue = self.cmd_queue[-10:]
        self.state = {"policy": self.policy, "loop_rate_hz": 1.0, "commands": cmds,
                      "queue_len": len(self.cmd_queue), "decision_latency_ms": 12.0}
        return self.get_state()

    def get_modbus_registers(self) -> dict[int, tuple[str, str, float, str]]:
        return {41200: ("policy", "enum", 1.0, ""),
                41201: ("loop_rate_hz", "uint16", 0.1, "Hz")}
