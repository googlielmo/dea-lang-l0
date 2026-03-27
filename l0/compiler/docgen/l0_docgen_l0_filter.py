# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
"""Helpers for rewriting L0 sources for Doxygen consumption."""

from __future__ import annotations

import re

_STRUCT_START_RE = re.compile(r"^(?P<indent>\s*)struct\s+[A-Za-z_][A-Za-z0-9_]*\s*\{\s*(?://.*)?$")
_ENUM_START_RE = re.compile(r"^(?P<indent>\s*)enum\s+[A-Za-z_][A-Za-z0-9_]*\s*\{\s*(?://.*)?$")
_FUNC_START_RE = re.compile(r"^(?P<indent>\s*)(?P<prefix>extern\s+)?func\s+[A-Za-z_][A-Za-z0-9_]*\s*\(")
_FIELD_RE = re.compile(
    r"^(?P<indent>\s*)(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<type>[^;]+?)\s*;\s*(?P<comment>//.*)?$"
)
_ENUM_VALUE_RE = re.compile(
    r"^(?P<indent>\s*)(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?P<assign>\s*=\s*[^;]+)?\s*;\s*(?P<comment>//.*)?$"
)
_FUNC_SIGNATURE_RE = re.compile(
    r"^(?P<indent>\s*)(?P<prefix>extern\s+)?func\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"\((?P<params>.*)\)\s*(?:->\s*(?P<return>[^{]+?))?\s*\{\s*(?P<comment>//.*)?$"
)
_FUNC_DECL_RE = re.compile(
    r"^(?P<indent>\s*)(?P<prefix>extern\s+)?func\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"\((?P<params>.*)\)\s*(?:->\s*(?P<return>[^;]+?))?\s*;\s*(?P<comment>//.*)?$"
)


def _normalize_field_type(type_text: str) -> tuple[str, bool]:
    normalized = " ".join(type_text.split())
    is_nullable = normalized.endswith("?")
    if is_nullable:
        normalized = normalized[:-1].rstrip()
    return normalized, is_nullable


def _format_decl_type(type_text: str) -> str:
    normalized, is_nullable = _normalize_field_type(type_text)
    if is_nullable:
        return f"{normalized} /* nullable */"
    return normalized


def _rewrite_function_signature(signature_lines: list[str]) -> str | None:
    normalized = " ".join(line.strip() for line in signature_lines)
    match = _FUNC_SIGNATURE_RE.match(normalized)
    terminator = "{"
    if not match:
        match = _FUNC_DECL_RE.match(normalized)
        terminator = ";"
    if not match:
        return None

    params_text = match.group("params").strip()
    rendered_params: list[str] = []
    if params_text:
        for param in params_text.split(","):
            name_and_type = param.strip()
            if not name_and_type:
                continue
            if ":" not in name_and_type:
                return None
            name, type_text = name_and_type.split(":", 1)
            rendered_params.append(f"{_format_decl_type(type_text)} {name.strip()}")

    return_type = _format_decl_type(match.group("return") or "void")
    prefix = match.group("prefix") or ""
    comment = f" {match.group('comment')}" if match.group("comment") else ""
    terminator_text = " {" if terminator == "{" else ";"
    return (
        f"{match.group('indent')}{prefix}{return_type} {match.group('name')}"
        f"({', '.join(rendered_params)}){terminator_text}{comment}\n"
    )


def transform_l0_for_doxygen(source: str) -> str:
    """Rewrite L0 declarations into a more C-like form for Doxygen."""
    lines = source.splitlines(keepends=True)
    output: list[str] = []
    struct_depth = 0
    enum_depth = 0
    func_signature_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        if func_signature_lines:
            func_signature_lines.append(line)
            if "{" in line or ";" in line:
                rewritten = _rewrite_function_signature(func_signature_lines)
                if rewritten is None:
                    output.extend(func_signature_lines)
                else:
                    output.append(rewritten)
                func_signature_lines = []
            continue

        if struct_depth == 0 and _STRUCT_START_RE.match(line):
            struct_depth = 1
            output.append(line)
            continue
        if enum_depth == 0 and _ENUM_START_RE.match(line):
            enum_depth = 1
            output.append(line)
            continue
        if struct_depth == 0 and enum_depth == 0 and _FUNC_START_RE.match(line):
            func_signature_lines = [line]
            if "{" in line or ";" in line:
                rewritten = _rewrite_function_signature(func_signature_lines)
                if rewritten is None:
                    output.extend(func_signature_lines)
                else:
                    output.append(rewritten)
                func_signature_lines = []
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

    if func_signature_lines:
        output.extend(func_signature_lines)

    return "".join(output)
