"""
dynamo_driver.py — DynamoDriver: connects to DynamoDB via aioboto3.

URL scheme: pynosqlc:dynamodb:<region>
  e.g. pynosqlc:dynamodb:us-east-1

Auto-registers with DriverManager on import.
"""

from __future__ import annotations

import os

import aioboto3

from pynosqlc.core.driver import Driver
from pynosqlc.core.driver_manager import DriverManager
from pynosqlc.dynamodb.dynamo_client import DynamoClient


class DynamoDriver(Driver):
    """Driver that creates :class:`DynamoClient` instances.

    URL prefix: ``pynosqlc:dynamodb:``
    """

    URL_PREFIX: str = "pynosqlc:dynamodb:"

    def accepts_url(self, url: str) -> bool:
        """Return ``True`` for ``'pynosqlc:dynamodb:'`` URLs."""
        return isinstance(url, str) and url.startswith(self.URL_PREFIX)

    async def connect(
        self,
        url: str,
        properties: dict | None = None,
    ) -> DynamoClient:
        """Create and return an open :class:`DynamoClient`.

        Args:
            url: ``pynosqlc:dynamodb:<region>``
            properties: optional dict; supports:
                - ``endpoint``: override endpoint URL (e.g. for DynamoDB Local)
                - ``aws_access_key_id``: AWS access key (optional)
                - ``aws_secret_access_key``: AWS secret key (optional)

        Returns:
            An open :class:`DynamoClient`.
        """
        props = properties or {}

        region = url[len(self.URL_PREFIX):]
        if not region:
            region = "us-east-1"

        endpoint = props.get("endpoint") or os.environ.get("DYNAMODB_ENDPOINT")

        session_kwargs: dict = {}
        if endpoint:
            # When using a local endpoint (DynamoDB Local / LocalStack) without
            # real credentials, supply dummy values so boto3 does not raise a
            # NoCredentialsError.
            has_real_creds = (
                os.environ.get("AWS_ACCESS_KEY_ID")
                or os.environ.get("AWS_PROFILE")
                or os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
                or os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE")
            )
            if not has_real_creds:
                session_kwargs["aws_access_key_id"] = props.get(
                    "aws_access_key_id", "dummy"
                )
                session_kwargs["aws_secret_access_key"] = props.get(
                    "aws_secret_access_key", "dummy"
                )

        session = aioboto3.Session(**session_kwargs)

        client = DynamoClient(url, session, region, endpoint, props)
        await client._open()
        return client


# Auto-register on import — a single shared instance is sufficient.
_driver = DynamoDriver()
DriverManager.register_driver(_driver)
