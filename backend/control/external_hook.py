"""External (Lighthouse) policy hook (spec §2.2.13.4)."""
from __future__ import annotations

from typing import Any

EXTERNAL: dict[str, Any] = {}


def set_external(commands: dict[str, Any]) -> dict[str, Any]:
    EXTERNAL.clear()
    EXTERNAL.update(commands)
    return dict(EXTERNAL)


def external_policy(ctx: dict[str, Any]) -> dict[str, Any]:
    online = bool((ctx.get("grid") or {}).get("online", True))
    return {
        "fronius_setpoint_pct": float(EXTERNAL.get("fronius_setpoint_pct", 1.0)),
        "quattro_mode": str(EXTERNAL.get("quattro_mode", "grid-tied" if online else "off-grid")),
        "quattro_command_w": float(EXTERNAL.get("quattro_command_w", 0.0)),
        "generator_enable": bool(EXTERNAL.get("generator_enable", False)),
        "generator_request_w": float(EXTERNAL.get("generator_request_w", 0.0)),
        "dcdc_enable": bool(EXTERNAL.get("dcdc_enable", False)),
        "mts_position": str(EXTERNAL.get("mts_position", "inverter")),
        "chroma_mode": str(EXTERNAL.get("chroma_mode", "load")),
        "chroma_power_w": float(EXTERNAL.get("chroma_power_w", 0.0)),
    }
