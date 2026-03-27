"""
dynamo_client.py — DynamoClient: a pynosqlc Client backed by aioboto3 DynamoDB resource.
"""

from __future__ import annotations

import botocore.exceptions

from pynosqlc.core.client import Client
from pynosqlc.dynamodb.dynamo_collection import DynamoCollection


class DynamoClient(Client):
    """A pynosqlc Client backed by an aioboto3 DynamoDB resource.

    Args:
        url: the original ``pynosqlc:dynamodb:<region>`` URL.
        session: an :class:`aioboto3.Session` instance.
        region: the AWS region name.
        endpoint: optional endpoint URL override (e.g. for DynamoDB Local).
        properties: driver-specific properties dict.
    """

    def __init__(
        self,
        url: str,
        session,
        region: str,
        endpoint: str | None,
        properties: dict | None = None,
    ) -> None:
        super().__init__({"url": url})
        self._session = session
        self._region = region
        self._endpoint = endpoint
        self._properties = properties or {}
        self._resource = None
        self._resource_ctx = None
        self._table_cache: set[str] = set()

    async def _open(self) -> None:
        """Enter the aioboto3 DynamoDB resource context manager.

        Must be called by the driver after constructing this client.
        """
        self._resource_ctx = self._session.resource(
            "dynamodb",
            region_name=self._region,
            endpoint_url=self._endpoint,
        )
        self._resource = await self._resource_ctx.__aenter__()

    def _get_collection(self, name: str) -> DynamoCollection:
        """Create and return a :class:`DynamoCollection` for *name*."""
        return DynamoCollection(self, name)

    async def _close(self) -> None:
        """Exit the aioboto3 DynamoDB resource context manager."""
        if self._resource_ctx is not None:
            await self._resource_ctx.__aexit__(None, None, None)
            self._resource_ctx = None
            self._resource = None

    async def ensure_table(self, name: str) -> None:
        """Ensure the DynamoDB table *name* exists, creating it if necessary.

        Uses ``_pk`` (String) as the partition key and ``PAY_PER_REQUEST``
        billing so no capacity planning is required.

        Idempotent: if the table already exists (verified or from cache),
        this is a no-op.

        Args:
            name: the DynamoDB table name.
        """
        if name in self._table_cache:
            return

        table = await self._resource.Table(name)

        # Check whether the table exists.
        try:
            await table.load()
            # Table exists — cache it and return.
            self._table_cache.add(name)
            return
        except botocore.exceptions.ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code not in ("ResourceNotFoundException",):
                raise

        # Table does not exist — create it.
        try:
            await self._resource.create_table(
                TableName=name,
                KeySchema=[{"AttributeName": "_pk", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "_pk", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )
        except botocore.exceptions.ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code not in ("ResourceInUseException", "TableAlreadyExistsException"):
                raise
            # Race: another coroutine already created the table — that's fine.

        # Wait for the table to become ACTIVE.
        waiter_table = await self._resource.Table(name)
        await waiter_table.wait_until_exists()
        self._table_cache.add(name)
