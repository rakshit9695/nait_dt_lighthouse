"""Control policy registry."""
from __future__ import annotations

from typing import Any, Callable

from backend.control.carbon_aware import carbon_aware_policy
from backend.control.economic_dispatch import economic_dispatch_policy
from backend.control.external_hook import external_policy
from backend.control.rule_baseline import rule_baseline_policy

POLICIES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "rule_baseline": rule_baseline_policy,
    "economic": economic_dispatch_policy,
    "carbon_aware": carbon_aware_policy,
    "external": external_policy,
}
