#!/usr/bin/env python3
"""
Generate `tests/e2e/testids.py` from `frontend/lib/testids.ts`.

Keeps the Python E2E test suite in sync with the TypeScript source of truth
for `data-testid` values used by page objects.

Usage:
    python3 scripts/generate_testids.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


# --- Locate project root and files ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = PROJECT_ROOT / "frontend" / "lib" / "testids.ts"
OUTPUT_FILE = PROJECT_ROOT / "tests" / "e2e" / "testids.py"


# --- Regex patterns ---
# Matches:  key: "value",   (allowing single or double quotes)
STATIC_RE = re.compile(
    r"""^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*["']([^"']+)["']\s*,?\s*$"""
)

# Matches an arrow-function entry:
#   key: (arg: type) => `prefix-${arg}`,
# We capture: key, arg-name, template body (with ${arg} placeholders).
ARROW_RE = re.compile(
    r"""^\s*([A-Za-z_][A-Za-z0-9_]*)      # key
        \s*:\s*
        \(\s*([A-Za-z_][A-Za-z0-9_]*)\s*  # arg name
        :\s*[^)]+\)                       # : type
        \s*=>\s*
        `([^`]*)`                         # template literal body
        \s*,?\s*$""",
    re.VERBOSE,
)


def parse_testids(source: str) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    """
    Parse the TS file content and return (statics, arrows).

    statics: list of (key, value) for `key: "value"` entries.
    arrows:  list of (key, arg_name, template_body) for arrow-function entries.
    """
    statics: list[tuple[str, str]] = []
    arrows: list[tuple[str, str, str]] = []

    for raw_line in source.splitlines():
        # Skip comment-only lines
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
            continue

        m = ARROW_RE.match(raw_line)
        if m:
            key, arg_name, template = m.group(1), m.group(2), m.group(3)
            arrows.append((key, arg_name, template))
            continue

        m = STATIC_RE.match(raw_line)
        if m:
            key, value = m.group(1), m.group(2)
            statics.append((key, value))
            continue

    return statics, arrows


def template_to_fstring_body(template: str, arg_name: str) -> str:
    """
    Convert a JS template literal body like `cart-item-${productId}` into the
    body of a Python f-string like `cart-item-{productId}`.

    Only substitutes references to the single arrow-function argument.
    """
    # Replace ${arg_name} with {arg_name}
    pattern = re.compile(r"\$\{\s*" + re.escape(arg_name) + r"\s*\}")
    return pattern.sub("{" + arg_name + "}", template)


def render_python(
    statics: list[tuple[str, str]],
    arrows: list[tuple[str, str, str]],
) -> str:
    """Render the output Python file content."""
    lines: list[str] = []
    lines.append('"""')
    lines.append("AUTO-GENERATED FILE - DO NOT EDIT MANUALLY.")
    lines.append("")
    lines.append("Generated from frontend/lib/testids.ts by scripts/generate_testids.py.")
    lines.append("To update: edit testids.ts, then run `make generate-testids`.")
    lines.append('"""')
    lines.append("from types import SimpleNamespace")
    lines.append("")
    lines.append("")
    lines.append("# --- Static testids ---")
    for key, value in statics:
        lines.append(f'{key} = "{value}"')

    lines.append("")
    lines.append("")
    lines.append("# --- Dynamic testids ---")
    for key, arg_name, template in arrows:
        body = template_to_fstring_body(template, arg_name)
        lines.append(f"def {key}({arg_name}: str) -> str:")
        lines.append(f'    return f"{body}"')
        lines.append("")

    lines.append("")
    lines.append("# --- Namespace for `from ... import TEST_IDS` style access ---")
    lines.append("TEST_IDS = SimpleNamespace(")
    for key, _ in statics:
        lines.append(f"    {key}={key},")
    for key, _, _ in arrows:
        lines.append(f"    {key}={key},")
    lines.append(")")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    if not SOURCE_FILE.exists():
        print(
            f"ERROR: source file not found: {SOURCE_FILE}\n"
            "A sibling task should create frontend/lib/testids.ts first.",
            file=sys.stderr,
        )
        return 1

    source = SOURCE_FILE.read_text(encoding="utf-8")
    statics, arrows = parse_testids(source)

    if not statics and not arrows:
        print(
            f"ERROR: parsed 0 entries from {SOURCE_FILE}. Regex may be out of sync.",
            file=sys.stderr,
        )
        return 2

    output = render_python(statics, arrows)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(output, encoding="utf-8")

    print(
        f"Generated {OUTPUT_FILE.relative_to(PROJECT_ROOT)}: "
        f"{len(statics)} constants, {len(arrows)} functions."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
