# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
"""Helpers for rewriting L0 sources for Doxygen consumption."""

from __future__ import annotations

import re

_STRUCT_START_RE = re.compile(r"^(?P<indent>\s*)struct\s+[A-Za-z_][A-Za-z0-9_]*\s*\{\s*(?://.*)?$")
_ENUM_START_RE = re.compile(r"^(?P<indent>\s*)enum\s+[A-Za-z_][A-Za-z0-9_]*\s*\{\s*(?://.*)?$")
_FIELD_RE = re.compile(
    r"^(?P<indent>\s*)(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<type>[^;]+?)\s*;\s*(?P<comment>//.*)?$"
)
_ENUM_VALUE_RE = re.compile(
    r"^(?P<indent>\s*)(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?P<assign>\s*=\s*[^;]+)?\s*;\s*(?P<comment>//.*)?$"
)


def _normalize_field_type(type_text: str) -> tuple[str, bool]:
    normalized = " ".join(type_text.split())
    is_nullable = normalized.endswith("?")
    if is_nullable:
        normalized = normalized[:-1].rstrip()
    return normalized, is_nullable


def transform_l0_for_doxygen(source: str) -> str:
    """Rewrite L0 declarations into a more C-like form for Doxygen."""
    lines = source.splitlines(keepends=True)
    output: list[str] = []
    struct_depth = 0
    enum_depth = 0

    for line in lines:
        stripped = line.strip()

        if struct_depth == 0 and _STRUCT_START_RE.match(line):
            struct_depth = 1
            output.append(line)
            continue
        if enum_depth == 0 and _ENUM_START_RE.match(line):
            enum_depth = 1
            output.append(line)
            continue

        if struct_depth > 0:
            struct_depth += line.count("{")
            struct_depth -= line.count("}")

            match = _FIELD_RE.match(line)
            if match and stripped != "}":
                field_type, is_nullable = _normalize_field_type(match.group("type"))
                nullable_note = " /* nullable */" if is_nullable else ""
                comment = f" {match.group('comment')}" if match.group("comment") else ""
                output.append(
                    f"{match.group('indent')}{field_type} {match.group('name')};{nullable_note}{comment}\n"
                )
                continue
            if stripped == "}":
                output.append(line.replace("}", "};", 1))
                continue

        if enum_depth > 0:
            enum_depth += line.count("{")
            enum_depth -= line.count("}")

            match = _ENUM_VALUE_RE.match(line)
            if match and stripped != "}":
                assign = match.group("assign") or ""
                comment = f" {match.group('comment')}" if match.group("comment") else ""
                output.append(f"{match.group('indent')}{match.group('name')}{assign},{comment}\n")
                continue
            if stripped == "}":
                output.append(line.replace("}", "};", 1))
                continue

        output.append(line)

    return "".join(output)
