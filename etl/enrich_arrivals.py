"""Helpers to enrich TfL arrivals payloads with line and stop point metadata."""

from __future__ import annotations

import logging
import os
from typing import Dict, Iterable, List, Optional

import requests
from requests import Session

from .extract_tfl import TFL_BASE_URL, get_http_session, get_line_routes

logger = logging.getLogger(__name__)

__all__ = [
    "fetch_stop_point_metadata",
    "enrich_arrivals_with_metadata",
]


def _normalise_line_id(line_id: Optional[str]) -> Optional[str]:
    if not line_id:
        return None
    return line_id.strip().lower()


def _simplify_line_record(record: dict) -> dict:
    return {
        "id": record.get("lineId") or record.get("id"),
        "name": record.get("lineName") or record.get("name"),
        "modeName": record.get("modeName"),
        "serviceTypes": record.get("serviceTypes"),
        "routeSections": record.get("routeSections"),
    }


def _build_line_metadata_map(records: Iterable[dict]) -> Dict[str, dict]:
    metadata: Dict[str, dict] = {}
    for record in records:
        line_id = record.get("lineId") or record.get("id")
        normalised = _normalise_line_id(line_id)
        if not normalised:
            continue
        metadata[normalised] = _simplify_line_record(record)
    return metadata


def _simplify_stop_point(record: dict) -> dict:
    return {
        "id": record.get("id"),
        "naptanId": record.get("naptanId"),
        "commonName": record.get("commonName"),
        "lat": record.get("lat"),
        "lon": record.get("lon"),
        "zone": record.get("zone"),
        "stopType": record.get("stopType"),
        "icsCode": record.get("icsCode"),
        "modes": record.get("modes"),
        "lines": record.get("lines"),
    }


def _build_stop_point_map(records: Iterable[dict]) -> Dict[str, dict]:
    metadata: Dict[str, dict] = {}
    for record in records:
        stop_id = record.get("naptanId") or record.get("id")
        if not stop_id:
            continue
        metadata[stop_id] = _simplify_stop_point(record)
    return metadata


def fetch_stop_point_metadata(
    stop_point_id: str,
    *,
    session: Optional[Session] = None,
    app_id: Optional[str] = None,
    app_key: Optional[str] = None,
    timeout: float = 10.0,
) -> dict:
    """Fetch metadata for a single stop point from the TfL API."""

    if not stop_point_id:
        raise ValueError("stop_point_id must be provided")

    session = session or get_http_session()
    app_id = app_id or os.getenv("TFL_APP_ID")
    app_key = app_key or os.getenv("TFL_APP_KEY")

    params = {}
    if app_id and app_key:
        params["app_id"] = app_id
        params["app_key"] = app_key

    url = f"{TFL_BASE_URL}/StopPoint/{stop_point_id}"
    try:
        response = session.get(url, params=params or None, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("TfL stop point request failed for %s: %s", stop_point_id, exc)
        raise RuntimeError("Failed to fetch stop point metadata") from exc

    try:
        data = response.json()
    except ValueError as exc:
        logger.warning("TfL stop point response was not JSON for %s", stop_point_id)
        raise RuntimeError("TfL API did not return JSON for stop point") from exc

    if not isinstance(data, dict):
        logger.warning(
            "Unexpected stop point payload type %s for %s",
            type(data).__name__,
            stop_point_id,
        )
        raise RuntimeError("Unexpected TfL stop point response type")

    return data


def enrich_arrivals_with_metadata(
    arrivals: List[dict],
    *,
    line_routes: Optional[List[dict]] = None,
    stop_points: Optional[List[dict]] = None,
    session: Optional[Session] = None,
    app_id: Optional[str] = None,
    app_key: Optional[str] = None,
    line_service_types: Optional[List[str]] = None,
    line_modes: Optional[List[str]] = None,
    timeout: float = 10.0,
) -> List[dict]:
    """Enrich TfL arrivals records with line and stop metadata."""

    if not arrivals:
        return []

    session = session or get_http_session()

    line_metadata_map: Dict[str, dict] = {}
    if line_routes is None:
        unique_line_ids = sorted(
            {
                normalised
                for arrival in arrivals
                for normalised in [_normalise_line_id(arrival.get("lineId"))]
                if normalised
            }
        )
        if unique_line_ids:
            line_routes = get_line_routes(
                line_ids=unique_line_ids,
                service_types=line_service_types,
                modes=line_modes,
                session=session,
                timeout=timeout,
            )
    if line_routes:
        line_metadata_map = _build_line_metadata_map(line_routes)

    stop_point_map: Dict[str, dict] = {}
    if stop_points is None:
        unique_stop_ids = sorted(
            {
                arrival.get("naptanId")
                or arrival.get("stopPointId")
                or arrival.get("stationId")
                or arrival.get("stopId")
                for arrival in arrivals
                if arrival.get("naptanId")
                or arrival.get("stopPointId")
                or arrival.get("stationId")
                or arrival.get("stopId")
            }
        )

        stop_point_records: List[dict] = []
        for stop_id in unique_stop_ids:
            try:
                record = fetch_stop_point_metadata(
                    stop_id,
                    session=session,
                    app_id=app_id,
                    app_key=app_key,
                    timeout=timeout,
                )
            except RuntimeError:
                continue
            stop_point_records.append(record)
        stop_points = stop_point_records

    if stop_points:
        stop_point_map = _build_stop_point_map(stop_points)

    enriched: List[dict] = []
    for arrival in arrivals:
        enriched_record = dict(arrival)

        line_key = _normalise_line_id(arrival.get("lineId"))
        if line_key and line_key in line_metadata_map:
            enriched_record["lineMetadata"] = line_metadata_map[line_key]

        stop_id = (
            arrival.get("naptanId")
            or arrival.get("stopPointId")
            or arrival.get("stationId")
            or arrival.get("stopId")
        )
        if stop_id and stop_id in stop_point_map:
            enriched_record["stopPointMetadata"] = stop_point_map[stop_id]

        enriched.append(enriched_record)

    return enriched


