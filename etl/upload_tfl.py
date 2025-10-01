"""Utility for exporting TfL route metadata snapshots to S3."""

import gzip
import io
import json
import logging
import os
from datetime import datetime
from typing import List, Optional

import boto3

from .extract_tfl import get_line_routes

logger = logging.getLogger(__name__)


def _resolve_s3_config(
    bucket: Optional[str],
    key_prefix: Optional[str],
    aws_region: Optional[str],
):
    bucket_name = bucket or os.getenv("TFL_S3_BUCKET")
    prefix = key_prefix or os.getenv("TFL_S3_PREFIX", "")
    region = aws_region or os.getenv("AWS_DEFAULT_REGION")

    if not bucket_name:
        raise ValueError("S3 bucket must be provided via argument or TFL_S3_BUCKET env")

    return bucket_name, prefix, region


def upload_line_routes_to_s3(
    bucket: Optional[str] = None,
    key_prefix: Optional[str] = None,
    line_ids: Optional[List[str]] = None,
    service_types: Optional[List[str]] = None,
    modes: Optional[List[str]] = None,
    compress: bool = True,
    aws_region: Optional[str] = None,
) -> str:
    """Fetch line routes and upload the payload to S3, returning the object key."""

    bucket_name, prefix, region = _resolve_s3_config(bucket, key_prefix, aws_region)

    routes = get_line_routes(
        line_ids=line_ids,
        service_types=service_types,
        modes=modes,
    )

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"line-routes-{timestamp}.json"
    data_bytes: bytes

    if compress:
        filename += ".gz"
        buffer = io.BytesIO()
        with gzip.GzipFile(filename=filename, mode="wb", fileobj=buffer) as gz:
            gz.write(json.dumps(routes, ensure_ascii=False).encode("utf-8"))
        data_bytes = buffer.getvalue()
    else:
        data_bytes = json.dumps(routes, ensure_ascii=False).encode("utf-8")

    object_key = f"{prefix.rstrip('/')}/{filename}" if prefix else filename

    session = boto3.session.Session(region_name=region)
    s3_client = session.client("s3")
    s3_client.put_object(Bucket=bucket_name, Key=object_key, Body=data_bytes)

    logger.info("Uploaded line route payload to s3://%s/%s", bucket_name, object_key)
    return object_key

