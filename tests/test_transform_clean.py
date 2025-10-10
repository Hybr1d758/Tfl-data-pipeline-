import pandas as pd
import pytest

from etl.transform_clean import (
    DEFAULT_OUTPUT_ORDER,
    REQUIRED_OUTPUT_COLUMNS,
    transform_arrivals,
    validate_arrivals_dataframe,
)


@pytest.fixture
def sample_records():
    base = {
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

    duplicate = dict(base)
    duplicate["id"] = "duplicate"

    return [base, duplicate]


@pytest.fixture
def edge_case_records():
    return [
        {
            "id": "missing-times",
            "lineId": "central",
            "platformName": "Platform 1",
            "destinationName": "West Ruislip",
            "timeToStation": "45",
            "naptanId": "940GZZLUEBY",
            "stationId": "940GZZLUEBY",
            "modeName": "tube",
        },
        {
            "id": "bus-mode",
            "lineId": "25",
            "platformName": "Stop B",
            "destinationName": "Oxford Circus",
            "expectedArrival": "2025-10-09T12:00:00Z",
            "timeToStation": 90,
            "naptanId": "490000235W",
            "modeName": "bus",
            "timestamp": "2025-10-09T11:55:00Z",
        },
    ]


def test_transform_arrivals_normalises_schema(sample_records):
    dataframe = transform_arrivals(sample_records)

    assert len(dataframe) == 1

    ordered = [col for col in DEFAULT_OUTPUT_ORDER if col in dataframe.columns]
    assert list(dataframe.columns[: len(ordered)]) == ordered

    assert dataframe.loc[0, "line_id"] == "central"
    assert dataframe.loc[0, "stop_point_id"] == "940GZZLUEBY"
    assert dataframe.loc[0, "time_to_station_seconds"] == 330

    assert dataframe["time_to_station_seconds"].dtype == "Int64"
    assert isinstance(dataframe["expected_arrival"].dtype, pd.DatetimeTZDtype)
    assert isinstance(dataframe["reported_at"].dtype, pd.DatetimeTZDtype)


def test_validate_arrivals_dataframe_missing_required_columns(sample_records):
    dataframe = transform_arrivals(sample_records)
    dataframe = dataframe.drop(columns=["stop_point_id"])

    with pytest.raises(ValueError) as exc:
        validate_arrivals_dataframe(dataframe)

    assert "Missing required columns" in str(exc.value)


def test_validate_arrivals_dataframe_null_required_columns(sample_records):
    dataframe = transform_arrivals(sample_records)
    for column in REQUIRED_OUTPUT_COLUMNS:
        dataframe[column] = pd.NA

    with pytest.raises(ValueError) as exc:
        validate_arrivals_dataframe(dataframe)

    assert "only null" in str(exc.value)


def test_transform_arrivals_handles_missing_fields(edge_case_records):
    dataframe = transform_arrivals(edge_case_records)

    assert len(dataframe) == 2

    missing_times_row = dataframe.loc[dataframe["line_id"] == "central"].iloc[0]
    assert pd.isna(missing_times_row["expected_arrival"])
    assert pd.isna(missing_times_row["reported_at"])
    assert missing_times_row["time_to_station_seconds"] == 45


def test_transform_arrivals_supports_mixed_modes(edge_case_records):
    dataframe = transform_arrivals(edge_case_records)

    assert set(dataframe["mode_name"].dropna()) == {"tube", "bus"}


