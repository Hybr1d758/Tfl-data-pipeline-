"""Batch orchestration utilities for fetching, enriching, and cleaning TfL arrivals."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence

from .enrich_arrivals import enrich_arrivals_with_metadata
from .extract_tfl import get_tfl_data
from .transform_clean import run_pipeline

logger = logging.getLogger(__name__)


FetchArrivals = Callable[[str], List[dict]]


@dataclass
class StopPointResult:
    stop_point_id: str
    arrivals_count: int
    enriched_count: int
    cleaned_count: int
    error: Optional[str] = None


def orchestrate_stop_points(
    stop_point_ids: Sequence[str],
    *,
    fetch_arrivals: Optional[FetchArrivals] = None,
    output_dir: Optional[Path] = None,
    line_service_types: Optional[Sequence[str]] = None,
    line_modes: Optional[Sequence[str]] = None,
) -> List[StopPointResult]:
    """Run the full pipeline for each stop ID and optionally persist outputs."""

    fetch_arrivals = fetch_arrivals or get_tfl_data
    results: List[StopPointResult] = []

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    for stop_id in stop_point_ids:
        logger.info("Starting orchestration for stop %s", stop_id)
        try:
            arrivals = fetch_arrivals(stop_id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to fetch arrivals for stop %s: %s", stop_id, exc)
            results.append(
                StopPointResult(
                    stop_point_id=stop_id,
                    arrivals_count=0,
                    enriched_count=0,
                    cleaned_count=0,
                    error=str(exc),
                )
            )
            continue

        if not arrivals:
            logger.warning("No arrivals returned for stop %s", stop_id)
            results.append(
                StopPointResult(
                    stop_point_id=stop_id,
                    arrivals_count=0,
                    enriched_count=0,
                    cleaned_count=0,
                    error=None,
                )
            )
            continue

        enriched = enrich_arrivals_with_metadata(
            arrivals,
            line_service_types=list(line_service_types) if line_service_types else None,
            line_modes=list(line_modes) if line_modes else None,
        )
        cleaned_df = run_pipeline(enriched)

        if output_dir:
            enriched_path = output_dir / f"{stop_id}_enriched.json"
            cleaned_path = output_dir / f"{stop_id}_cleaned.csv"
            enriched_path.write_text(
                json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            cleaned_df.to_csv(cleaned_path, index=False)
            logger.info(
                "Persisted outputs for %s to %s", stop_id, output_dir
            )

        results.append(
            StopPointResult(
                stop_point_id=stop_id,
                arrivals_count=len(arrivals),
                enriched_count=len(enriched),
                cleaned_count=len(cleaned_df),
                error=None,
            )
        )

    return results


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stop-point",
        dest="stop_points",
        action="append",
        help="Stop point ID to process (can be supplied multiple times).",
    )
    parser.add_argument(
        "--stop-points-file",
        type=Path,
        help="Path to a text file with one stop point ID per line.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory where enriched JSON and cleaned CSV will be written.",
    )
    parser.add_argument(
        "--line-service-types",
        nargs="*",
        help="Optional filter for TfL line service types (e.g. Regular).",
    )
    parser.add_argument(
        "--line-modes",
        nargs="*",
        help="Optional filter for TfL modes (e.g. tube, bus).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging output.",
    )

    args = parser.parse_args(argv)

    stop_points: List[str] = []
    if args.stop_points:
        stop_points.extend(args.stop_points)
    if args.stop_points_file:
        content = args.stop_points_file.read_text(encoding="utf-8")
        stop_points.extend([line.strip() for line in content.splitlines() if line.strip()])

    if not stop_points:
        parser.error("Provide at least one stop ID via --stop-point or --stop-points-file")

    args.stop_points = stop_points
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    _configure_logging(args.verbose)

    results = orchestrate_stop_points(
        args.stop_points,
        output_dir=args.output_dir,
        line_service_types=args.line_service_types,
        line_modes=args.line_modes,
    )

    successful = [result for result in results if result.error is None]
    failed = [result for result in results if result.error]

    logger.info(
        "Completed orchestration | successful: %s | failed: %s",
        len(successful),
        len(failed),
    )

    if failed:
        logger.warning("Failed stops: %s", ", ".join(r.stop_point_id for r in failed))
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


