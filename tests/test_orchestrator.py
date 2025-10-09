import pandas as pd
import pytest

from etl.orchestrator import StopPointResult, orchestrate_stop_points


@pytest.fixture
def mock_fetch_arrivals():
    def _fetch(stop_point_id: str):
        if stop_point_id == "empty":
            return []
        if stop_point_id == "error":
            raise RuntimeError("boom")
        return [
            {
                "id": "abc123",
                "lineId": "central",
                "platformName": "Eastbound Platform 2",
                "destinationName": "Epping",
                "expectedArrival": "2025-10-09T11:32:30Z",
                "timeToStation": 330,
                "naptanId": "940GZZLUEBY",
                "stationId": "940GZZLUEBY",
                "modeName": "tube",
                "timestamp": "2025-10-09T11:27:00Z",
                "vehicleId": "987",
                "towards": "Epping",
                "direction": "outbound",
            }
        ]

    return _fetch


def test_orchestrate_stop_points_handles_success_and_failures(tmp_path, mock_fetch_arrivals):
    stop_ids = ["940GZZLUEBY", "empty", "error"]

    results = orchestrate_stop_points(
        stop_ids,
        fetch_arrivals=mock_fetch_arrivals,
        output_dir=tmp_path,
    )

    assert len(results) == 3

    success_result = next(r for r in results if r.stop_point_id == "940GZZLUEBY")
    assert success_result.arrivals_count == 1
    assert success_result.cleaned_count == 1
    assert success_result.error is None

    empty_result = next(r for r in results if r.stop_point_id == "empty")
    assert empty_result.arrivals_count == 0
    assert empty_result.cleaned_count == 0
    assert empty_result.error is None

    error_result = next(r for r in results if r.stop_point_id == "error")
    assert error_result.error == "boom"

    enriched_path = tmp_path / "940GZZLUEBY_enriched.json"
    cleaned_path = tmp_path / "940GZZLUEBY_cleaned.csv"
    assert enriched_path.exists()
    assert cleaned_path.exists()

    cleaned_df = pd.read_csv(cleaned_path)
    assert list(cleaned_df.columns[:4]) == [
        "line_id",
        "mode_name",
        "platform_name",
        "destination_name",
    ]


