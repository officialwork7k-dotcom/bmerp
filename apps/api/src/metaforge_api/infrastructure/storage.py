"""S3-compatible storage adapter — the only place a provider SDK call is
allowed to appear, per the required stack ("Access only through the storage
adapter interface... never hardcode a provider-specific SDK call outside
that adapter")."""

from __future__ import annotations

import uuid

import boto3

from metaforge_api.infrastructure.settings import settings


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )


def put_object(filename: str, content: bytes, content_type: str) -> str:
    object_key = f"{uuid.uuid4()}/{filename}"
    _client().put_object(Bucket=settings.s3_bucket, Key=object_key, Body=content, ContentType=content_type)
    return object_key


def get_object(object_key: str) -> bytes:
    return _client().get_object(Bucket=settings.s3_bucket, Key=object_key)["Body"].read()


def presigned_get_url(object_key: str, expires_seconds: int = 3600) -> str:
    return _client().generate_presigned_url(
        "get_object", Params={"Bucket": settings.s3_bucket, "Key": object_key}, ExpiresIn=expires_seconds
    )
