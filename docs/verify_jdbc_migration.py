"""
verify_jdbc_migration.py — checks that docs/jdbc-migration.md is well-formed.

Checks:
  1. File exists and is readable
  2. Required section headings present (DriverManager, Collection, Filter,
     Async, Cursor each appear in a '## ' heading line)
  3. Every ```python ... ``` block parses without syntax errors
  4. Concept Mapping Table exists ('| JDBC' or '| Class.forName' present)
  5. Key pynosqlc-specific details are documented (await pattern, sync
     get_collection, bool next(), get_document, trailing underscores)

Exits 0 if all checks pass; exits 1 on the first failure.
"""

import ast
import re
import sys
from pathlib import Path


def die(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"ok: {msg}")


def main() -> None:
    doc_path = Path(__file__).parent / "jdbc-migration.md"

    # ── Check 1: file exists ──────────────────────────────────────────────
    if not doc_path.exists():
        die(f"{doc_path} not found")
    text = doc_path.read_text(encoding="utf-8")
    ok("docs/jdbc-migration.md exists and is readable")

    # ── Check 2: required section headings ───────────────────────────────
    heading_lines = [
        line for line in text.splitlines() if line.startswith("## ")
    ]
    heading_text = "\n".join(heading_lines)

    required_keywords = {
        "DriverManager": "DriverManager section",
        "Collection": "Collections section",
        "Filter": "Filter section",
        "Async": "Async-Only API section",
        "Cursor": "Cursors section",
    }
    for keyword, description in required_keywords.items():
        if keyword not in heading_text:
            die(
                f"Missing required heading containing '{keyword}'. "
                f"Found headings:\n{heading_text}"
            )
    ok("all required section headings present (DriverManager, Collection, Filter, Async, Cursor)")

    # ── Check 3: all Python code blocks parse ────────────────────────────
    python_blocks = re.findall(r"```python\n(.*?)```", text, re.DOTALL)
    if not python_blocks:
        die("no ```python code blocks found in docs/jdbc-migration.md")

    parse_errors = []
    for i, block in enumerate(python_blocks, start=1):
        try:
            ast.parse(block)
        except SyntaxError as exc:
            parse_errors.append(f"block {i}: {exc}")

    if parse_errors:
        die("Python code block(s) failed to parse:\n" + "\n".join(parse_errors))
    ok(f"all {len(python_blocks)} Python code block(s) parse without syntax errors")

    # ── Check 4: Concept Mapping Table exists ────────────────────────────
    if "| JDBC" not in text and "| Class.forName" not in text:
        die(
            "Concept Mapping Table not found "
            "(expected '| JDBC' or '| Class.forName' in the document)"
        )
    ok("Concept Mapping Table present")

    # ── Check 5: key correctness details documented ───────────────────────
    correctness_checks = {
        "async with await": (
            "'async with await' pattern documented "
            "(critical: await before async with for get_client)"
        ),
        "get_collection": (
            "'get_collection' documented (sync method, no await)"
        ),
        "get_document": (
            "'get_document' documented (retrieves current doc after next())"
        ),
        "cursor.next()": (
            "'cursor.next()' returns bool documented"
        ),
        "in_()": (
            "trailing-underscore keyword methods documented (in_(), and_(), etc.)"
        ),
    }
    for snippet, description in correctness_checks.items():
        if snippet not in text:
            die(f"Missing required detail: {description!r} (searched for {snippet!r})")
    ok("all critical correctness details documented (await pattern, sync get_collection, "
       "bool next(), get_document, trailing underscores)")

    print()
    print("All checks passed.")


if __name__ == "__main__":
    main()
