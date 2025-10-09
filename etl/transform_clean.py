"""Clean and validate TfL arrivals payloads before loading downstream."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import pandas as pd

from .extract_tfl import arrivals_to_dataframe

logger = logging.getLogger(__name__)


COLUMN_RENAMES = {
    "lineId": "line_id",
    "platformName": "platform_name",
    "destinationName": "destination_name",
    "expectedArrival": "expected_arrival",
    "timeToStation": "time_to_station_seconds",
    "naptanId": "stop_point_id",
    "stationId": "station_id",
    "modeName": "mode_name",
    "timestamp": "reported_at",
    "currentLocation": "current_location",
    "towards": "towards",
    "direction": "direction",
    "vehicleId": "vehicle_id",
}

REQUIRED_OUTPUT_COLUMNS = [
    "line_id",
    "stop_point_id",
    "expected_arrival",
    "time_to_station_seconds",
]

DEFAULT_OUTPUT_ORDER = [
    "line_id",
    "mode_name",
    "platform_name",
    "destination_name",
    "towards",
    "direction",
    "current_location",
    "vehicle_id",
    "stop_point_id",
    "station_id",
    "expected_arrival",
    "reported_at",
    "time_to_station_seconds",
]

DATETIME_COLUMNS = ["expected_arrival", "reported_at"]
INTEGER_COLUMNS = ["time_to_station_seconds"]


def transform_arrivals(records: Sequence[dict]) -> pd.DataFrame:
    """Return a cleaned DataFrame with canonical column names and types."""

    dataframe = arrivals_to_dataframe(list(records))
    if dataframe.empty:
        return pd.DataFrame(columns=DEFAULT_OUTPUT_ORDER)

    dataframe = dataframe.rename(columns=COLUMN_RENAMES)

    for source, target in COLUMN_RENAMES.items():
        if target not in dataframe.columns:
            if source in dataframe.columns:
                dataframe[target] = dataframe.pop(source)
            else:
                dataframe[target] = pd.NA

    for column in REQUIRED_OUTPUT_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = pd.NA

    for column in INTEGER_COLUMNS:
        if column in dataframe.columns:
            dataframe[column] = pd.to_numeric(
                dataframe[column], errors="coerce"
            ).astype("Int64")

    for column in DATETIME_COLUMNS:
        if column in dataframe.columns:
            dataframe[column] = pd.to_datetime(
                dataframe[column], errors="coerce", utc=True
            )

    dataframe = dataframe.drop_duplicates(
        subset=[col for col in ["vehicle_id", "expected_arrival", "stop_point_id"] if col in dataframe.columns]
    )

    ordered_columns = [col for col in DEFAULT_OUTPUT_ORDER if col in dataframe.columns]
    remaining_columns = [col for col in dataframe.columns if col not in ordered_columns]
    dataframe = dataframe[ordered_columns + remaining_columns]

    return dataframe


def validate_arrivals_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Raise if required columns contain nulls or are missing entirely."""

    missing = [col for col in REQUIRED_OUTPUT_COLUMNS if col not in dataframe.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    null_issues = [
        col for col in REQUIRED_OUTPUT_COLUMNS if dataframe[col].isna().all()
    ]
    if null_issues:
        raise ValueError(f"Required columns contain only null values: {null_issues}")

    return dataframe


def _load_records_from_path(path: Path) -> List[dict]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Failed to read arrivals payload: {path}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Input file is not valid JSON: {path}") from exc

    if isinstance(payload, dict):
        records = payload.get("records") or payload.get("arrivals")
        if records is None:
            raise RuntimeError("JSON object must contain 'records' or 'arrivals'")
        payload = records

    if not isinstance(payload, list):
        raise RuntimeError("Arrivals payload must be a JSON array")

    return payload


def _demo_records() -> List[dict]:
    return [
        {
            "id": "123456789",
            "lineId": "central",
            "platformName": "Westbound - Platform 1",
            "destinationName": "West Ruislip",
            "expectedArrival": "2025-10-09T11:30:00Z",
            "timeToStation": 180,
            "naptanId": "940GZZLUEBY",
            "stationId": "940GZZLUEBY",
            "modeName": "tube",
            "timestamp": "2025-10-09T11:27:00Z",
            "vehicleId": "123",
            "towards": "West Ruislip",
            "direction": "inbound",
        },
        {
            "id": "987654321",
            "lineId": "central",
            "platformName": "Eastbound - Platform 2",
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
        },
    ]


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def run_pipeline(records: Sequence[dict]) -> pd.DataFrame:
    dataframe = transform_arrivals(records)
    return validate_arrivals_dataframe(dataframe)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to arrivals JSON payload (list or object with 'records'/'arrivals').",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write cleaned CSV output.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use a small built-in demo payload instead of reading from disk.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging output.",
    )
    args = parser.parse_args(argv)

    if not args.demo and not args.input:
        parser.error("provide --input PATH or use --demo")

    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    _configure_logging(args.verbose)

    if args.demo:
        logger.info("Running demo transform_clean pipeline")
        records = _demo_records()
    else:
        logger.info("Loading arrivals payload from %s", args.input)
        records = _load_records_from_path(args.input)

    dataframe = run_pipeline(records)
    logger.info("Cleaned %s arrivals records", len(dataframe))

    if args.output:
        dataframe.to_csv(args.output, index=False)
        logger.info("Wrote cleaned payload to %s", args.output)
    else:
        preview = dataframe.head().to_dict(orient="records")
        print(json.dumps(preview, default=str, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


