from custom_components.llm_gateway.satellite_diagnostics import (
    first_failing_check,
    satellite_diagnostic_snapshot,
)


def test_satellite_diagnostic_snapshot_reads_recorder_safe_projection(hass) -> None:
    hass.states.async_set(
        "sensor.kukui_diagnostic_snapshot",
        "warning",
        {
            "schema_version": 1,
            "generated_at": "2026-07-12T01:55:19+00:00",
            "check_count": 30,
            "status_counts": {"ok": 26, "warning": 1, "blocked": 3},
            "non_ok_count": 4,
            "non_ok_checks": [
                {
                    "id": "acoustic.measurement.available",
                    "status": "warning",
                    "layer": "acoustic",
                    "repair_hint": "Install a real measurement report.",
                },
                {
                    "id": "acoustic.barge_in.measured",
                    "status": "blocked",
                    "layer": "acoustic",
                    "depends_on": ["acoustic.measurement.available"],
                    "repair_hint": "Measure barge-in.",
                },
            ],
            "full_snapshot_endpoint": ("http://127.0.0.1:10710/diagnostic-snapshot"),
        },
    )

    snapshot = satellite_diagnostic_snapshot(hass)

    assert snapshot["projection"] == "recorder_safe_compact"
    assert snapshot["complete"] is False
    assert snapshot["summary"]["check_count"] == 30
    assert snapshot["summary"]["status_counts"]["blocked"] == 3
    assert len(snapshot["checks"]) == 2
    assert snapshot["first_failing_check"]["id"] == ("acoustic.measurement.available")
    assert snapshot["first_failing_check"]["blocking_dependents"] == [
        "acoustic.barge_in.measured"
    ]


def test_first_failing_check_ignores_blocked_checks() -> None:
    first = first_failing_check(
        [
            {
                "id": "acoustic.barge_in.measured",
                "status": "blocked",
                "layer": "acoustic",
                "depends_on": ["acoustic.measurement.available"],
            },
            {
                "id": "acoustic.measurement.available",
                "status": "warning",
                "layer": "acoustic",
            },
        ]
    )

    assert first["id"] == "acoustic.measurement.available"


def test_first_failing_check_returns_empty_for_only_blocked_checks() -> None:
    first = first_failing_check(
        [
            {
                "id": "acoustic.barge_in.measured",
                "status": "blocked",
                "layer": "acoustic",
                "depends_on": ["acoustic.measurement.available"],
            }
        ]
    )

    assert first == {}
