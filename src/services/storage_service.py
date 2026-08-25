from __future__ import annotations

import os

import boto3

_BUCKET_NAME = os.environ.get("AUDIO_STORAGE_BUCKET", "az1-audio")

_client = boto3.client(
    "s3",
    endpoint_url=os.environ.get("AUDIO_STORAGE_ENDPOINT_URL", "http://localhost:9000"),
    region_name=os.environ.get("AUDIO_STORAGE_REGION", "us-east-1"),
    aws_access_key_id=os.environ.get("AUDIO_STORAGE_ACCESS_KEY", "minioadmin"),
    aws_secret_access_key=os.environ.get("AUDIO_STORAGE_SECRET_KEY", "minioadmin"),
)


def store_audio(key: str, content: bytes, content_type: str) -> None:
    _client.put_object(Bucket=_BUCKET_NAME, Key=key, Body=content, ContentType=content_type)
