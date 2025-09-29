import logging
import os
from typing import List, Optional

import pandas as pd
import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

TFL_BASE_URL = "https://api.tfl.gov.uk"
_session: Optional[Session] = None


def _build_session(max_retries: int = 3, backoff_factor: float = 0.5) -> Session:
    """Create a requests session with retry/backoff behaviour."""
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_http_session() -> Session:
    """Return a module-level session, creating it on first use."""
    global _session
    if _session is None:
        _session = _build_session()
    return _session


def get_tfl_data(
    stop_point_id: str,
    app_id: Optional[str] = None,
    app_key: Optional[str] = None,
    timeout: float = 10.0,
    session: Optional[Session] = None,
) -> List[dict]:
    """
    Fetch arrivals for a TfL stop point.
    Credentials sourced from args or env: TFL_APP_ID / TFL_APP_KEY.
    """
    app_id = app_id or os.getenv("TFL_APP_ID")
    app_key = app_key or os.getenv("TFL_APP_KEY")
    if not app_id or not app_key:
        raise ValueError("Missing TfL credentials (TFL_APP_ID/TFL_APP_KEY).")

    url = f"{TFL_BASE_URL}/stoppoint/{stop_point_id}/arrivals"
    session = session or get_http_session()
    logger.info("Fetching TfL arrivals for stop %s", stop_point_id)

    try:
        resp = session.get(
            url,
            params={"app_id": app_id, "app_key": app_key},
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("TfL request failed for stop %s: %s", stop_point_id, exc)
        raise RuntimeError("Failed to fetch data from TfL API") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        logger.warning("TfL response was not JSON for stop %s", stop_point_id)
        raise RuntimeError("TfL API did not return JSON.") from exc

    if not isinstance(data, list):
        logger.warning("Unexpected TfL response type %s", type(data).__name__)
        raise RuntimeError(f"Unexpected TfL response type: {type(data).__name__}")

    logger.debug("Fetched %d arrival records for stop %s", len(data), stop_point_id)
    return data


def extract_tfl_data(stop_point_id: str, **kwargs) -> List[dict]:
    """Thin wrapper kept for backwards compatibility."""
    return get_tfl_data(stop_point_id, **kwargs)


def arrivals_to_dataframe(arrivals: List[dict]) -> pd.DataFrame:
    """Optional: normalize arrivals to a DataFrame."""
    if not arrivals:
        return pd.DataFrame()
    return pd.json_normalize(arrivals)