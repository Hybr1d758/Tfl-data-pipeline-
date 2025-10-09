"""End-to-end pipeline that fetches, enriches, and cleans TfL arrivals."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Optional, Sequence

from .enrich_arrivals import enrich_arrivals_with_metadata
from .extract_tfl import get_tfl_data
from .transform_clean import run_pipeline

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stop_point_id",
        help="TfL stop point identifier (e.g. 940GZZLUEBY).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write cleaned arrivals as CSV.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to write enriched arrivals payload as JSON.",
    )
    parser.add_argument(
        "--line-service-types",
        nargs="*",
        help="Filter enrichments to specific line service types (e.g. Regular).",
    )
    parser.add_argument(
        "--line-modes",
        nargs="*",
        help="Filter enrichments to specific modes (e.g. tube, bus).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging output.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    _configure_logging(args.verbose)

    logger.info("Fetching arrivals for stop %s", args.stop_point_id)
    try:
        arrivals = get_tfl_data(args.stop_point_id)
    except ValueError as exc:
        logger.error("Failed to fetch arrivals: %s", exc)
        return 1
    if not arrivals:
        logger.warning("No arrivals returned for stop %s", args.stop_point_id)
        return 0

    logger.info("Enriching %s arrivals with line and stop metadata", len(arrivals))
    enriched = enrich_arrivals_with_metadata(
        arrivals,
        line_service_types=args.line_service_types,
        line_modes=args.line_modes,
    )

    if args.output_json:
        args.output_json.write_text(json.dumps(enriched, ensure_ascii=False, indent=2))
        logger.info("Wrote enriched arrivals JSON to %s", args.output_json)

    logger.info("Cleaning enriched arrivals payload")
    dataframe = run_pipeline(enriched)
    logger.info("Cleaned %s arrivals records", len(dataframe))

    if args.output:
        dataframe.to_csv(args.output, index=False)
        logger.info("Wrote cleaned arrivals CSV to %s", args.output)
    else:
        preview = dataframe.head().to_dict(orient="records")
        print(json.dumps(preview, default=str, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


