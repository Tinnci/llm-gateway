from custom_components.llm_gateway.satellite_diagnostics import first_failing_check


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
