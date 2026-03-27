"""
compliance.py — Shared driver compliance test suite for pynosqlc drivers.

Usage in a driver package's test file::

    from pynosqlc.core.testing import run_compliance
    from pynosqlc.core import DriverManager
    import pynosqlc.memory

    async def _factory():
        DriverManager.clear()
        import pynosqlc.memory  # re-registers the driver
        return await DriverManager.get_client('pynosqlc:memory:')

    run_compliance(_factory)

``run_compliance`` uses ``sys._getframe(1).f_globals`` to inject a set of
pytest ``Test*`` classes directly into the calling module's namespace so that
pytest's standard discovery collects them automatically.

Arguments:
    client_factory: ``async def () -> Client`` — called before each test class
                    to produce a fresh, open client.
    skip_find:      if ``True``, the find-operator test class is omitted
                    (useful for backends that do not support scan/filter).
"""

from __future__ import annotations

import sys
from typing import Any, Callable, Coroutine

import pytest

from pynosqlc.core.filter import Filter


def run_compliance(
    client_factory: Callable[[], Coroutine[Any, Any, Any]],
    *,
    skip_find: bool = False,
) -> None:
    """Register compliance test classes into the calling module's namespace.

    Pytest discovers ``Test*`` classes from module globals at collection time.
    This function injects those classes before collection completes by writing
    directly into ``sys._getframe(1).f_globals``.

    Args:
        client_factory: Async callable returning an open :class:`~pynosqlc.core.Client`.
        skip_find: When ``True``, the find-operator test class is not registered.
    """
    caller_globals = sys._getframe(1).f_globals

    # ── KV test class ──────────────────────────────────────────────────────

    class TestKVCompliance:
        """Key-value compliance: store/get, delete, upsert."""

        @pytest.fixture(autouse=True)
        async def _setup(self):
            self.client = await client_factory()
            self.col = self.client.get_collection("compliance_kv")
            yield
            if not self.client.is_closed():
                await self.client.close()

        async def test_store_and_get_retrieves_document(self):
            await self.col.store("kv-1", {"name": "Alice", "age": 30})
            doc = await self.col.get("kv-1")
            assert doc is not None
            assert doc["name"] == "Alice"
            assert doc["age"] == 30

        async def test_get_returns_none_for_missing_key(self):
            import time
            doc = await self.col.get(f"kv-nonexistent-{int(time.time() * 1000)}")
            assert doc is None

        async def test_store_overwrites_existing_document(self):
            await self.col.store("kv-upsert", {"name": "Bob", "age": 25})
            await self.col.store("kv-upsert", {"name": "Bob", "age": 26})
            doc = await self.col.get("kv-upsert")
            assert doc is not None
            assert doc["age"] == 26

        async def test_delete_removes_document(self):
            await self.col.store("kv-del", {"name": "ToDelete"})
            await self.col.delete("kv-del")
            doc = await self.col.get("kv-del")
            assert doc is None

        async def test_delete_missing_key_does_not_raise(self):
            import time
            await self.col.delete(f"kv-missing-{int(time.time() * 1000)}")

    # ── Document test class ────────────────────────────────────────────────

    class TestDocumentCompliance:
        """Document compliance: insert, update."""

        @pytest.fixture(autouse=True)
        async def _setup(self):
            self.client = await client_factory()
            self.col = self.client.get_collection("compliance_doc")
            yield
            if not self.client.is_closed():
                await self.client.close()

        async def test_insert_returns_an_id(self):
            id_ = await self.col.insert({"name": "Charlie", "status": "active"})
            assert isinstance(id_, str)
            assert len(id_) > 0

        async def test_inserted_document_retrievable_by_id(self):
            id_ = await self.col.insert({"name": "Dana", "score": 99})
            doc = await self.col.get(id_)
            assert doc is not None
            assert doc["name"] == "Dana"

        async def test_two_inserts_produce_different_ids(self):
            id1 = await self.col.insert({"name": "E1"})
            id2 = await self.col.insert({"name": "E2"})
            assert id1 != id2

        async def test_update_patches_fields_without_destroying_others(self):
            await self.col.store("upd-1", {"name": "Frank", "age": 40, "country": "AU"})
            await self.col.update("upd-1", {"age": 41})
            doc = await self.col.get("upd-1")
            assert doc is not None
            assert doc["age"] == 41
            assert doc["name"] == "Frank"
            assert doc["country"] == "AU"

    # ── Lifecycle test class ───────────────────────────────────────────────

    class TestLifecycleCompliance:
        """Client lifecycle compliance."""

        @pytest.fixture(autouse=True)
        async def _setup(self):
            self.client = await client_factory()
            yield
            if not self.client.is_closed():
                await self.client.close()

        def test_get_collection_returns_same_instance(self):
            c1 = self.client.get_collection("same-name")
            c2 = self.client.get_collection("same-name")
            assert c1 is c2

        def test_is_closed_false_for_open_client(self):
            assert self.client.is_closed() is False

    # ── Register classes into caller's module globals ──────────────────────

    caller_globals["TestKVCompliance"] = TestKVCompliance
    caller_globals["TestDocumentCompliance"] = TestDocumentCompliance
    caller_globals["TestLifecycleCompliance"] = TestLifecycleCompliance

    # ── Find test class (optional) ─────────────────────────────────────────

    if skip_find:
        return

    class TestFindCompliance:
        """Find-with-filter compliance: all operators + cursor iteration."""

        # Seed data: same 5 docs as JS compliance suite
        _SEED = [
            ("f1", {"name": "Alice", "age": 30, "status": "active",   "tags": ["js", "ts"], "score": 85}),
            ("f2", {"name": "Bob",   "age": 25, "status": "inactive", "tags": ["py"],        "score": 70}),
            ("f3", {"name": "Charlie", "age": 35, "status": "active", "tags": ["js", "go"], "score": 90}),
            ("f4", {"name": "Dana", "age": 22, "status": "pending",   "tags": ["ts"],        "score": 60}),
            ("f5", {"name": "Eve",  "age": 30, "status": "active",    "score": 95, "email": "eve@example.com"}),
        ]

        @pytest.fixture(autouse=True)
        async def _setup(self):
            self.client = await client_factory()
            self.fcol = self.client.get_collection("compliance_find")
            for key, doc in self._SEED:
                await self.fcol.store(key, doc)
            yield
            if not self.client.is_closed():
                await self.client.close()

        async def test_eq_finds_matching_documents(self):
            cursor = await self.fcol.find(Filter.where("status").eq("active").build())
            docs = cursor.get_documents()
            await cursor.close()
            assert len(docs) == 3
            assert all(d["status"] == "active" for d in docs)

        async def test_ne_finds_non_matching_documents(self):
            cursor = await self.fcol.find(Filter.where("status").ne("active").build())
            docs = cursor.get_documents()
            await cursor.close()
            assert len(docs) == 2
            assert all(d["status"] != "active" for d in docs)

        async def test_gt_finds_documents_greater_than_value(self):
            cursor = await self.fcol.find(Filter.where("age").gt(29).build())
            docs = cursor.get_documents()
            await cursor.close()
            assert len(docs) >= 2
            assert all(d["age"] > 29 for d in docs)

        async def test_lt_finds_documents_less_than_value(self):
            cursor = await self.fcol.find(Filter.where("age").lt(25).build())
            docs = cursor.get_documents()
            await cursor.close()
            assert all(d["age"] < 25 for d in docs)

        async def test_gte_finds_documents_gte_value(self):
            cursor = await self.fcol.find(Filter.where("score").gte(90).build())
            docs = cursor.get_documents()
            await cursor.close()
            assert all(d["score"] >= 90 for d in docs)
            assert len(docs) >= 2

        async def test_lte_finds_documents_lte_value(self):
            cursor = await self.fcol.find(Filter.where("score").lte(70).build())
            docs = cursor.get_documents()
            await cursor.close()
            assert all(d["score"] <= 70 for d in docs)

        async def test_contains_finds_array_field_contains_value(self):
            cursor = await self.fcol.find(Filter.where("tags").contains("js").build())
            docs = cursor.get_documents()
            await cursor.close()
            assert len(docs) >= 2
            assert all("js" in d["tags"] for d in docs)

        async def test_in_finds_documents_with_field_in_values(self):
            cursor = await self.fcol.find(
                Filter.where("status").in_(["active", "pending"]).build()
            )
            docs = cursor.get_documents()
            await cursor.close()
            assert all(d["status"] in ["active", "pending"] for d in docs)
            assert len(docs) >= 3

        async def test_nin_finds_documents_with_field_not_in_values(self):
            cursor = await self.fcol.find(
                Filter.where("status").nin(["inactive", "pending"]).build()
            )
            docs = cursor.get_documents()
            await cursor.close()
            assert all(d["status"] not in ["inactive", "pending"] for d in docs)

        async def test_exists_true_finds_documents_where_field_present(self):
            cursor = await self.fcol.find(Filter.where("email").exists(True).build())
            docs = cursor.get_documents()
            await cursor.close()
            assert len(docs) >= 1
            assert all(d.get("email") is not None for d in docs)

        async def test_exists_false_finds_documents_where_field_absent(self):
            cursor = await self.fcol.find(Filter.where("email").exists(False).build())
            docs = cursor.get_documents()
            await cursor.close()
            assert all(d.get("email") is None for d in docs)

        async def test_compound_and_applies_both_conditions(self):
            ast = Filter.where("status").eq("active").and_("age").gt(29).build()
            cursor = await self.fcol.find(ast)
            docs = cursor.get_documents()
            await cursor.close()
            assert all(d["status"] == "active" and d["age"] > 29 for d in docs)
            assert len(docs) >= 1

        async def test_cursor_for_await_iteration(self):
            cursor = await self.fcol.find(Filter.where("status").eq("active").build())
            docs = []
            async for doc in cursor:
                docs.append(doc)
            assert len(docs) >= 3

    caller_globals["TestFindCompliance"] = TestFindCompliance
