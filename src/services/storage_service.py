from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, BinaryIO

import boto3
from botocore.exceptions import ClientError


@dataclass(frozen=True)
class S3StorageSettings:
    bucket_name: str
    endpoint_url: str
    region_name: str
    access_key: str
    secret_key: str

    @classmethod
    def from_environment(cls) -> S3StorageSettings:
        return cls(
            bucket_name=os.environ.get("AUDIO_STORAGE_BUCKET", "az1-audio"),
            endpoint_url=os.environ.get("AUDIO_STORAGE_ENDPOINT_URL", "http://localhost:9000"),
            region_name=os.environ.get("AUDIO_STORAGE_REGION", "us-east-1"),
            access_key=os.environ.get("AUDIO_STORAGE_ACCESS_KEY", "minioadmin"),
            secret_key=os.environ.get("AUDIO_STORAGE_SECRET_KEY", "minioadmin"),
        )


class S3AudioStorage:
    def __init__(self, client: Any, bucket_name: str) -> None:
        self._client = client
        self._bucket_name = bucket_name

    @classmethod
    def from_settings(cls, settings: S3StorageSettings) -> S3AudioStorage:
        client = boto3.client(
            "s3",
            endpoint_url=settings.endpoint_url,
            region_name=settings.region_name,
            aws_access_key_id=settings.access_key,
            aws_secret_access_key=settings.secret_key,
        )
        return cls(client=client, bucket_name=settings.bucket_name)

    def store(
        self,
        *,
        key: str,
        content: BinaryIO,
        content_type: str,
        metadata: dict[str, str],
    ) -> None:
        content.seek(0)
        self._client.put_object(
            Bucket=self._bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type,
            Metadata=metadata,
        )

    def fetch(self, *, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket_name, Key=key)
            return response["Body"].read()
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "NoSuchKey":
                raise KeyError(key) from exc
            raise
