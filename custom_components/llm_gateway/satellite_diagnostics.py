"""Helpers for reading Kukui satellite diagnostic snapshots from Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

SATELLITE_DIAGNOSTIC_SNAPSHOT_ENTITY_ID = "sensor.kukui_diagnostic_snapshot"


def satellite_diagnostic_snapshot(hass: HomeAssistant) -> dict[str, Any]:
    """Return the latest satellite diagnostic snapshot with derived blockers."""
    state = hass.states.get(SATELLITE_DIAGNOSTIC_SNAPSHOT_ENTITY_ID)
    if state is None:
        return {}
    snapshot = state.attributes.get("snapshot")
    if isinstance(snapshot, dict):
        return snapshot_with_first_failing_check(snapshot)
    return snapshot_with_first_failing_check(
        {
            "schema_version": state.attributes.get("schema_version"),
            "generated_at": state.attributes.get("generated_at"),
            "checks": state.attributes.get("checks") or [],
            "pipewire_graph": state.attributes.get("pipewire_graph") or {},
            "acoustic_measurement": state.attributes.get("acoustic_measurement") or {},
        }
    )


def snapshot_with_first_failing_check(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Attach the earliest failing dependency check when the source lacks one."""
    if "first_failing_check" in snapshot:
        return snapshot
    enriched = dict(snapshot)
    first = first_failing_check(enriched.get("checks"))
    if first:
        enriched["first_failing_check"] = first
    return enriched


def first_failing_check(checks: object) -> dict[str, Any]:
    """Return the earliest warning/error check by dependency depth and layer."""
    if not isinstance(checks, list):
        return {}
    by_id = {
        str(check.get("id")): check
        for check in checks
        if isinstance(check, dict) and check.get("id")
    }
    failing = {
        check_id
        for check_id, check in by_id.items()
        if str(check.get("status") or "") in {"warning", "error"}
    }
    if not failing:
        return {}

    def failing_depth(check_id: str, seen: set[str] | None = None) -> int:
        if check_id not in failing:
            return -1
        local_seen = set(seen or set())
        if check_id in local_seen:
            return 0
        local_seen.add(check_id)
        check = by_id.get(check_id) or {}
        dependencies = check.get("depends_on")
        if not isinstance(dependencies, list):
            return 0
        dependency_depths = [
            failing_depth(str(dep), local_seen)
            for dep in dependencies
            if str(dep) in failing
        ]
        return 0 if not dependency_depths else 1 + max(dependency_depths)

    selected_id = min(
        failing,
        key=lambda check_id: (
            failing_depth(check_id),
            0 if str(by_id[check_id].get("status")) == "error" else 1,
            _LAYER_ORDER.get(str(by_id[check_id].get("layer") or ""), 99),
            check_id,
        ),
    )
    selected = dict(by_id[selected_id])
    selected["blocking_dependents"] = sorted(
        check_id
        for check_id, check in by_id.items()
        if selected_id
        in [
            str(dep)
            for dep in (
                check.get("depends_on")
                if isinstance(check.get("depends_on"), list)
                else []
            )
        ]
    )
    return selected


_LAYER_ORDER = {
    "kernel": 0,
    "modules": 1,
    "firmware": 2,
    "udev": 3,
    "permissions": 4,
    "systemd": 5,
    "dbus": 6,
    "pipewire": 7,
    "service": 8,
    "homeassistant": 9,
    "asr": 10,
    "gateway": 11,
    "tts": 12,
    "acoustic": 13,
    "state": 14,
}
