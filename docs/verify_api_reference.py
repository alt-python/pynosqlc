#!/usr/bin/env python3
"""
docs/verify_api_reference.py

Exercises every public symbol and code pattern documented in docs/api-reference.md.
Run with:
    python docs/verify_api_reference.py

Requires pynosqlc-core and pynosqlc-memory to be installed (or on PYTHONPATH).
"""

import asyncio
import sys

# ---------------------------------------------------------------------------
# 1. Import all 9 public symbols from pynosqlc.core
# ---------------------------------------------------------------------------
from pynosqlc.core import (
    DriverManager,
    ClientDataSource,
    Client,
    Collection,
    Cursor,
    Filter,
    FieldCondition,
    Driver,
    UnsupportedOperationError,
)
import pynosqlc.memory  # auto-registers MemoryDriver

print("ok: import")


# ---------------------------------------------------------------------------
# 2. FieldCondition operators — all 10, including in_() AST key check
# ---------------------------------------------------------------------------

# eq
ast = Filter.where('status').eq('active').build()
assert ast == {'type': 'condition', 'field': 'status', 'op': 'eq', 'value': 'active'}, f"eq failed: {ast}"

# ne
ast = Filter.where('status').ne('deleted').build()
assert ast['op'] == 'ne', f"ne op wrong: {ast}"

# gt
ast = Filter.where('age').gt(18).build()
assert ast['op'] == 'gt', f"gt op wrong: {ast}"

# gte
ast = Filter.where('score').gte(90).build()
assert ast['op'] == 'gte', f"gte op wrong: {ast}"

# lt
ast = Filter.where('price').lt(100.0).build()
assert ast['op'] == 'lt', f"lt op wrong: {ast}"

# lte
ast = Filter.where('price').lte(50.0).build()
assert ast['op'] == 'lte', f"lte op wrong: {ast}"

# contains
ast = Filter.where('tags').contains('python').build()
assert ast['op'] == 'contains', f"contains op wrong: {ast}"
assert ast['value'] == 'python', f"contains value wrong: {ast}"

# in_ — critical: AST key must be 'in', not 'in_'
ast = Filter.where('role').in_(['admin', 'editor']).build()
assert ast['op'] == 'in', f"in_ should write op='in', got: {ast['op']}"
assert ast['value'] == ['admin', 'editor'], f"in_ value wrong: {ast}"

# nin
ast = Filter.where('status').nin(['deleted', 'banned']).build()
assert ast['op'] == 'nin', f"nin op wrong: {ast}"

# exists
ast = Filter.where('email').exists().build()
assert ast['op'] == 'exists', f"exists op wrong: {ast}"
assert ast['value'] is True, f"exists default value should be True: {ast}"

ast = Filter.where('deleted_at').exists(False).build()
assert ast['value'] is False, f"exists(False) value wrong: {ast}"

print("ok: filter ops")


# ---------------------------------------------------------------------------
# 3. Filter combinators: or_, not_(), build() with 0/1/multi conditions
# ---------------------------------------------------------------------------

# Zero conditions
empty_ast = Filter().build()
assert empty_ast == {'type': 'and', 'conditions': []}, f"zero conditions wrong: {empty_ast}"

# Single condition — build() returns the leaf directly
single = Filter.where('x').eq(1).build()
assert single == {'type': 'condition', 'field': 'x', 'op': 'eq', 'value': 1}, f"single wrong: {single}"

# Multi-condition AND
multi = Filter.where('age').gt(18).and_('role').eq('admin').build()
assert multi['type'] == 'and', f"multi type wrong: {multi}"
assert len(multi['conditions']) == 2, f"multi should have 2 conditions: {multi}"
assert multi['conditions'][0]['op'] == 'gt'
assert multi['conditions'][1]['op'] == 'eq'

# or_() with Filter instances
or_ast = Filter.or_(
    Filter.where('role').eq('admin'),
    Filter.where('role').eq('editor'),
)
assert or_ast['type'] == 'or', f"or_ type wrong: {or_ast}"
assert len(or_ast['conditions']) == 2, f"or_ should have 2 conditions: {or_ast}"

# or_() with three branches
or3 = Filter.or_(
    Filter.where('a').eq(1),
    Filter.where('b').eq(2),
    Filter.where('c').eq(3),
)
assert len(or3['conditions']) == 3, f"or_ with 3 args wrong: {or3}"

# not_()
not_ast = Filter.where('age').gte(18).not_()
assert not_ast['type'] == 'not', f"not_ type wrong: {not_ast}"
assert 'condition' in not_ast, f"not_ should have 'condition' key: {not_ast}"
assert not_ast['condition']['op'] == 'gte', f"not_ inner op wrong: {not_ast}"

# or_() with pre-built AST dicts
d1 = Filter.where('role').eq('admin').build()
d2 = Filter.where('role').eq('editor').build()
or_from_dicts = Filter.or_(d1, d2)
assert or_from_dicts['type'] == 'or'
assert len(or_from_dicts['conditions']) == 2

print("ok: filter combinators")


# ---------------------------------------------------------------------------
# 4. DriverManager: register, get_drivers, get_client (async), deregister, clear
# ---------------------------------------------------------------------------

# get_drivers returns a list
drivers_before = DriverManager.get_drivers()
assert isinstance(drivers_before, list), "get_drivers should return a list"
# pynosqlc.memory registers on import so there should be at least one
assert len(drivers_before) >= 1, "expected at least MemoryDriver registered"

# register_driver is idempotent
initial_count = len(DriverManager.get_drivers())
DriverManager.register_driver(drivers_before[0])  # re-register same instance
assert len(DriverManager.get_drivers()) == initial_count, "idempotent register failed"

# deregister_driver
from pynosqlc.memory import _driver as memory_driver  # type: ignore[import]
DriverManager.clear()
DriverManager.register_driver(memory_driver)
assert len(DriverManager.get_drivers()) == 1

DriverManager.deregister_driver(memory_driver)
assert len(DriverManager.get_drivers()) == 0, "deregister_driver failed"

# clear
DriverManager.register_driver(memory_driver)
DriverManager.register_driver(memory_driver)  # idempotent — still 1
DriverManager.clear()
assert len(DriverManager.get_drivers()) == 0, "clear failed"

# ValueError when no driver registered
async def _test_no_driver():
    try:
        await DriverManager.get_client('pynosqlc:memory:')
        assert False, "should have raised ValueError"
    except ValueError:
        pass  # expected

asyncio.run(_test_no_driver())

# Re-register for subsequent tests
DriverManager.register_driver(memory_driver)

print("ok: driver_manager")


# ---------------------------------------------------------------------------
# 5. ClientDataSource: constructor and get_url
# ---------------------------------------------------------------------------

ds = ClientDataSource({'url': 'pynosqlc:memory:'})
assert ds.get_url() == 'pynosqlc:memory:', f"get_url wrong: {ds.get_url()}"

# with optional fields
ds2 = ClientDataSource({
    'url': 'pynosqlc:memory:',
    'username': 'alice',
    'password': 'secret',
    'properties': {'timeout': 30},
})
assert ds2.get_url() == 'pynosqlc:memory:'

# missing url raises KeyError
try:
    ClientDataSource({})
    assert False, "should have raised KeyError"
except KeyError:
    pass  # expected

print("ok: client_data_source")


# ---------------------------------------------------------------------------
# 6. Memory driver roundtrip: connect, get_collection, store/get/insert/update/find+cursor
# ---------------------------------------------------------------------------

async def _memory_roundtrip():
    async with await DriverManager.get_client('pynosqlc:memory:') as client:
        # get_collection is sync
        col = client.get_collection('test_col')
        assert col.get_name() == 'test_col', f"get_name wrong: {col.get_name()}"

        # store / get
        await col.store('k1', {'name': 'Alice', 'age': 30, 'role': 'admin'})
        await col.store('k2', {'name': 'Bob', 'age': 25, 'role': 'editor'})
        await col.store('k3', {'name': 'Carol', 'age': 17, 'role': 'viewer'})

        doc = await col.get('k1')
        assert doc is not None, "get k1 returned None"
        assert doc['name'] == 'Alice', f"get k1 name wrong: {doc}"

        # get missing key → None
        missing = await col.get('no-such-key')
        assert missing is None, f"missing key should be None, got: {missing}"

        # insert
        key = await col.insert({'name': 'Dave', 'age': 40, 'role': 'owner'})
        assert isinstance(key, str), f"insert should return str, got: {type(key)}"
        dave = await col.get(key)
        assert dave['name'] == 'Dave', f"inserted doc wrong: {dave}"

        # update (shallow merge)
        await col.update('k1', {'age': 31})
        updated = await col.get('k1')
        assert updated['age'] == 31, f"update age wrong: {updated}"
        assert updated['name'] == 'Alice', f"update should preserve name: {updated}"

        # find + cursor
        ast = Filter.where('age').gt(18).build()
        cursor = await col.find(ast)
        assert not cursor.is_closed(), "cursor should not be closed yet"

        # get_documents (bulk, no iteration required)
        docs = cursor.get_documents()
        names = {d['name'] for d in docs}
        assert 'Alice' in names, f"Alice should be in results: {names}"
        assert 'Bob' in names, f"Bob should be in results: {names}"
        assert 'Carol' not in names, f"Carol (age 17) should not be in results: {names}"
        assert 'Dave' in names, f"Dave should be in results: {names}"

        # close
        await cursor.close()
        assert cursor.is_closed(), "cursor should be closed after close()"

        # client state
        assert not client.is_closed(), "client should not be closed yet"
        assert client.get_url() == 'pynosqlc:memory:', f"get_url wrong: {client.get_url()}"

    # after async with block
    assert client.is_closed(), "client should be closed after async with"

    print("ok: memory driver roundtrip")


asyncio.run(_memory_roundtrip())


# ---------------------------------------------------------------------------
# 7. Cursor iteration with async for
# ---------------------------------------------------------------------------

async def _cursor_iteration():
    async with await DriverManager.get_client('pynosqlc:memory:') as client:
        col = client.get_collection('iter_col')
        await col.store('i1', {'val': 1})
        await col.store('i2', {'val': 2})
        await col.store('i3', {'val': 3})

        ast = Filter.where('val').gte(1).build()
        cursor = await col.find(ast)

        seen_vals = []
        async for doc in cursor:
            seen_vals.append(doc['val'])

        assert len(seen_vals) == 3, f"expected 3 docs, got: {seen_vals}"
        assert set(seen_vals) == {1, 2, 3}, f"wrong values: {seen_vals}"

        # async for closes automatically on exhaustion
        assert cursor.is_closed(), "cursor should auto-close after async for"

        # manual next() loop on a fresh cursor
        cursor2 = await col.find(ast)
        manual_vals = []
        while await cursor2.next():
            manual_vals.append(cursor2.get_document()['val'])
        await cursor2.close()
        assert set(manual_vals) == {1, 2, 3}, f"manual iteration wrong: {manual_vals}"

    print("ok: cursor iteration")


asyncio.run(_cursor_iteration())


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print("All checks passed.")
