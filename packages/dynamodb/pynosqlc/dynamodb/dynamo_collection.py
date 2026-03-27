"""
dynamo_collection.py — DynamoCollection: a pynosqlc Collection backed by a DynamoDB table.

The primary key attribute is ``_pk`` (String). All other document fields are
stored as top-level DynamoDB item attributes.
"""

from __future__ import annotations

import uuid

from pynosqlc.core.collection import Collection
from pynosqlc.core.cursor import Cursor
from pynosqlc.dynamodb.dynamo_filter_translator import DynamoFilterTranslator


class DynamoCollection(Collection):
    """A pynosqlc Collection backed by a DynamoDB table.

    The DynamoDB table is created on first access with ``_pk`` as the
    partition key.  :meth:`DynamoClient.ensure_table` is called at the start
    of every operation — it is a no-op after the first successful call.

    Args:
        client: the owning :class:`~pynosqlc.dynamodb.DynamoClient`.
        name: the table / collection name.
    """

    def __init__(self, client, name: str) -> None:
        super().__init__(client, name)

    async def _get(self, key: str) -> dict | None:
        """Retrieve a document by its ``_pk``."""
        table = self._client._resource.Table(self._name)
        await self._client.ensure_table(self._name)

        resp = await table.get_item(Key={"_pk": key})
        item = resp.get("Item")
        if item is None:
            return None
        return {k: v for k, v in item.items() if k != "_pk"}

    async def _store(self, key: str, doc: dict) -> None:
        """Upsert a document, setting ``_pk = key``."""
        table = self._client._resource.Table(self._name)
        await self._client.ensure_table(self._name)

        await table.put_item(Item={**doc, "_pk": key})

    async def _delete(self, key: str) -> None:
        """Delete the document at ``_pk = key``."""
        table = self._client._resource.Table(self._name)
        await self._client.ensure_table(self._name)

        await table.delete_item(Key={"_pk": key})

    async def _insert(self, doc: dict) -> str:
        """Insert a document with a generated UUID ``_pk``; return the id."""
        table = self._client._resource.Table(self._name)
        await self._client.ensure_table(self._name)

        id_ = str(uuid.uuid4())
        await table.put_item(Item={**doc, "_pk": id_})
        return id_

    async def _update(self, key: str, patch: dict) -> None:
        """Patch the document at ``_pk = key`` using a SET expression.

        Only provided fields are updated; others are preserved.
        ``_pk`` is never patched even if present in *patch*.
        """
        table = self._client._resource.Table(self._name)
        await self._client.ensure_table(self._name)

        # Build SET expression: skip _pk to avoid overwriting the partition key.
        fields = [(k, v) for k, v in patch.items() if k != "_pk"]
        if not fields:
            return

        set_parts = []
        expr_names: dict[str, str] = {}
        expr_values: dict[str, object] = {}

        for i, (field, value) in enumerate(fields):
            name_alias = f"#attr{i}"
            value_alias = f":val{i}"
            set_parts.append(f"{name_alias} = {value_alias}")
            expr_names[name_alias] = field
            expr_values[value_alias] = value

        update_expr = "SET " + ", ".join(set_parts)

        await table.update_item(
            Key={"_pk": key},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )

    async def _find(self, ast: dict) -> Cursor:
        """Find documents matching the filter AST.

        Translates the AST to a DynamoDB FilterExpression, performs a full
        table scan with automatic pagination, strips ``_pk`` from each item,
        and wraps results in a :class:`~pynosqlc.core.Cursor`.
        """
        table = self._client._resource.Table(self._name)
        await self._client.ensure_table(self._name)

        filter_expr, attr_names, attr_values = DynamoFilterTranslator.translate(ast)

        scan_kwargs: dict = {}
        if filter_expr is not None:
            scan_kwargs["FilterExpression"] = filter_expr
            scan_kwargs["ExpressionAttributeNames"] = attr_names
            if attr_values:
                scan_kwargs["ExpressionAttributeValues"] = attr_values

        # Paginated scan.
        items: list[dict] = []
        resp = await table.scan(**scan_kwargs)
        items.extend(resp.get("Items", []))

        while "LastEvaluatedKey" in resp:
            resp = await table.scan(
                ExclusiveStartKey=resp["LastEvaluatedKey"],
                **scan_kwargs,
            )
            items.extend(resp.get("Items", []))

        # Strip the internal _pk field before returning to callers.
        docs = [{k: v for k, v in item.items() if k != "_pk"} for item in items]
        return Cursor(docs)
