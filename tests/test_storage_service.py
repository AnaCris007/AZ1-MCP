from __future__ import annotations

import io
import unittest
from unittest.mock import Mock

from services.storage_service import S3ObjectStorage


class TestS3ObjectStorage(unittest.TestCase):
    def test_envia_objeto_com_contrato_esperado(self) -> None:
        client = Mock()
        storage = S3ObjectStorage(client=client, bucket_name="az1-audio")
        content = io.BytesIO(b"audio")
        content.seek(2)

        storage.store(
            key="incoming/aud_123",
            content=content,
            content_type="audio/mpeg",
            metadata={"audio-format": "mp3"},
        )

        client.put_object.assert_called_once_with(
            Bucket="az1-audio",
            Key="incoming/aud_123",
            Body=content,
            ContentType="audio/mpeg",
            Metadata={"audio-format": "mp3"},
        )
        self.assertEqual(content.tell(), 0)


if __name__ == "__main__":
    unittest.main()
