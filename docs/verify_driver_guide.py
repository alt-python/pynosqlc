"""
verify_driver_guide.py — Verification script for docs/driver-guide.md

Checks:
1. Compliance factory wiring works against the real memory driver
   (DriverManager.clear + re-register + insert + get round-trip)
2. docs/driver-guide.md has exactly 5 '## Step' sections
3. '## Packaging' section exists
4. '## Reference Implementations' section exists
5. All fenced ```python ... ``` blocks that look like abstract skeletons
   parse cleanly via ast.parse()

Run with:
    .venv/bin/python docs/verify_driver_guide.py
"""

from __future__ import annotations

import ast
import asyncio
import os
import re
import sys

# ── Path setup ──────────────────────────────────────────────────────────────
# Script lives in docs/; project root is one level up.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "packages", "core"))
sys.path.insert(0, os.path.join(_ROOT, "packages", "memory"))

GUIDE_PATH = os.path.join(_HERE, "driver-guide.md")


# ── Check 1: compliance factory wiring ─────────────────────────────────────

async def _run_compliance_wiring() -> None:
    """
    Mirror the Step 5 pattern against the real memory driver:
      - DriverManager.clear()
      - re-register _driver
      - open a client
      - insert a doc
      - retrieve it by key
    """
    from pynosqlc.core import DriverManager
    from pynosqlc.memory.memory_driver import _driver  # noqa: F401

    DriverManager.clear()
    DriverManager.register_driver(_driver)

    client = await DriverManager.get_client("pynosqlc:memory:")
    async with client:
        col = client.get_collection("verify_wiring")
        key = await col.insert({"name": "guide-verify", "value": 42})
        doc = await col.get(key)
        assert doc is not None, "insert+get round-trip failed: doc is None"
        assert doc["name"] == "guide-verify", f"unexpected doc: {doc!r}"
        assert doc["value"] == 42, f"unexpected value: {doc['value']!r}"


def check_compliance_wiring() -> None:
    asyncio.run(_run_compliance_wiring())
    print("ok: compliance factory wiring (clear + re-register + insert + get)")


# ── Check 2: exactly 5 ## Step sections ────────────────────────────────────

def check_step_count() -> None:
    with open(GUIDE_PATH, encoding="utf-8") as fh:
        content = fh.read()
    steps = re.findall(r"^## Step", content, re.MULTILINE)
    count = len(steps)
    assert count == 5, f"expected 5 '## Step' sections, found {count}"
    print(f"ok: driver-guide.md has exactly {count} '## Step' sections")


# ── Check 3: ## Packaging section exists ───────────────────────────────────

def check_packaging_section() -> None:
    with open(GUIDE_PATH, encoding="utf-8") as fh:
        content = fh.read()
    assert re.search(r"^## Packaging", content, re.MULTILINE), \
        "'## Packaging' section not found in driver-guide.md"
    print("ok: '## Packaging' section exists")


# ── Check 4: ## Reference Implementations section exists ───────────────────

def check_reference_implementations_section() -> None:
    with open(GUIDE_PATH, encoding="utf-8") as fh:
        content = fh.read()
    assert re.search(r"^## Reference Implementations", content, re.MULTILINE), \
        "'## Reference Implementations' section not found in driver-guide.md"
    print("ok: '## Reference Implementations' section exists")


# ── Check 5: all python code blocks parse ──────────────────────────────────

def check_code_blocks_parse() -> None:
    with open(GUIDE_PATH, encoding="utf-8") as fh:
        content = fh.read()

    # Extract ```python ... ``` fenced blocks
    blocks = re.findall(r"```python\n(.*?)```", content, re.DOTALL)
    assert blocks, "no ```python blocks found in driver-guide.md"

    errors: list[str] = []
    parsed = 0
    for i, block in enumerate(blocks, start=1):
        try:
            ast.parse(block)
            parsed += 1
        except SyntaxError as exc:
            errors.append(f"block {i}: {exc}")

    if errors:
        raise AssertionError(
            f"{len(errors)} python block(s) failed to parse:\n" + "\n".join(errors)
        )
    print(f"ok: all {parsed} python code block(s) parse cleanly (ast.parse)")


# ── Runner ──────────────────────────────────────────────────────────────────

def main() -> None:
    checks = [
        check_compliance_wiring,
        check_step_count,
        check_packaging_section,
        check_reference_implementations_section,
        check_code_blocks_parse,
    ]
    for check in checks:
        try:
            check()
        except (AssertionError, Exception) as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            sys.exit(1)

    print("All checks passed.")


if __name__ == "__main__":
    main()
