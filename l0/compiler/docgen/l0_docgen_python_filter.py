# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
"""Helpers for rewriting Stage 1 Python sources for Doxygen consumption."""

from __future__ import annotations

import re
from ast import AsyncFunctionDef, ClassDef, Constant, Expr, FunctionDef, Module, get_docstring, parse
from collections import defaultdict
from dataclasses import dataclass
from inspect import cleandoc
from typing import Iterable

_SECTION_RE = re.compile(r"^(Args|Returns|Raises|Attributes|Note|See Also):\s*$")
_ENTRY_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)(?:\s*\([^)]*\))?:\s*(.*)$")
_RAISE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_\.]*):\s*(.*)$")
_BULLET_RE = re.compile(r"^\s*-\s+(.*)$")


@dataclass(frozen=True)
class SourceEdit:
    """A source transformation to apply."""

    start_line: int
    end_line: int
    replacement: list[str]


def _clean_lines(docstring: str) -> list[str]:
    return cleandoc(docstring).splitlines() if docstring else []


def _split_sections(docstring: str) -> tuple[list[str], dict[str, list[str]]]:
    lines = _clean_lines(docstring)
    intro: list[str] = []
    sections: dict[str, list[str]] = {}
    current = intro
    for line in lines:
        match = _SECTION_RE.match(line.strip())
        if match:
            current = sections.setdefault(match.group(1), [])
            continue
        current.append(line.rstrip())
    return intro, sections


def _paragraphs(lines: Iterable[str]) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            continue
        current.append(stripped)
    if current:
        paragraphs.append(" ".join(current).strip())
    return paragraphs


def _render_freeform_blocks(lines: list[str], indent: str) -> list[str]:
    blocks: list[tuple[str, list[str]]] = []
    paragraph_lines: list[str] = []
    bullet_items: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            blocks.append(("paragraph", [" ".join(part.strip() for part in paragraph_lines if part.strip()).strip()]))
            paragraph_lines = []

    def flush_bullets() -> None:
        nonlocal bullet_items
        if bullet_items:
            blocks.append(("bullets", bullet_items))
            bullet_items = []

    for line in lines:
        if not line.strip():
            flush_paragraph()
            flush_bullets()
            continue

        bullet_match = _BULLET_RE.match(line)
        if bullet_match:
            flush_paragraph()
            bullet_items.append(f"- {bullet_match.group(1).strip()}")
            continue

        if bullet_items and line[:1].isspace():
            bullet_items[-1] = f"{bullet_items[-1]} {line.strip()}"
            continue

        flush_bullets()
        paragraph_lines.append(line.strip())

    flush_paragraph()
    flush_bullets()

    rendered: list[str] = []
    for index, (kind, items) in enumerate(blocks):
        if index:
            rendered.append(f"{indent}#")
        if kind == "paragraph":
            rendered.append(f"{indent}# {_sanitize_text(items[0])}")
            continue
        for item in items:
            rendered.append(f"{indent}# {_sanitize_text(item)}")

    return rendered


def _parse_named_entries(lines: list[str], pattern: re.Pattern[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    name = ""
    current: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        match = pattern.match(line)
        if match:
            if name:
                entries.append((name, " ".join(current).strip()))
            name = match.group(1)
            current = [match.group(2).strip()] if match.group(2).strip() else []
            continue
        current.append(line.strip())
    if name:
        entries.append((name, " ".join(current).strip()))
    return entries


def _parse_returns(lines: list[str]) -> str:
    return " ".join(line.strip() for line in lines if line.strip()).strip()


def _render_blocks(lines: list[str]) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append(" ".join(current).strip())
                current = []
            continue
        if stripped.startswith("- ") and current:
            blocks.append(" ".join(current).strip())
            current = [stripped]
            continue
        current.append(stripped)
    if current:
        blocks.append(" ".join(current).strip())
    return blocks


def _sanitize_text(text: str) -> str:
    def replace_inline_code(match: re.Match[str]) -> str:
        content = match.group(1)
        if any(char.isspace() for char in content):
            return f'"{content}"'
        return f"@c {content}"

    text = re.sub(r"``([^`\n]+)``", replace_inline_code, text)
    text = re.sub(r"`([^`\n]+)`", replace_inline_code, text)
    return re.sub(r"(?<!\\)#(?=[A-Za-z_])", r"\\#", text)


def _build_comment_lines(docstring: str, indent: str) -> list[str]:
    intro, sections = _split_sections(docstring)
    intro_blocks = _render_freeform_blocks(intro, indent)
    if not intro_blocks and not any(sections.values()):
        return []

    comment_lines: list[str] = []
    if intro_blocks:
        first_line = intro_blocks[0]
        if first_line.startswith(f"{indent}# "):
            comment_lines.append(f"{indent}## {first_line[len(indent) + 2:]}")
            comment_lines.extend(intro_blocks[1:])
        else:
            comment_lines.append(f"{indent}##")
            comment_lines.extend(intro_blocks)
    else:
        comment_lines.append(f"{indent}##")

    for name, description in _parse_named_entries(sections.get("Args", []), _ENTRY_RE):
        comment_lines.append(f"{indent}#")
        comment_lines.append(f"{indent}# @param {name} {_sanitize_text(description)}".rstrip())

    returns = _parse_returns(sections.get("Returns", []))
    if returns:
        comment_lines.append(f"{indent}#")
        comment_lines.append(f"{indent}# @return {_sanitize_text(returns)}")

    for name, description in _parse_named_entries(sections.get("Raises", []), _RAISE_RE):
        comment_lines.append(f"{indent}#")
        comment_lines.append(f"{indent}# @exception {name} {_sanitize_text(description)}".rstrip())

    attributes = _parse_named_entries(sections.get("Attributes", []), _ENTRY_RE)
    if attributes:
        comment_lines.append(f"{indent}#")
        comment_lines.append(f"{indent}# @par Attributes")
        for name, description in attributes:
            comment_lines.append(f"{indent}# - @c {name}: {_sanitize_text(description)}".rstrip())

    note_blocks = _render_blocks(sections.get("Note", []))
    if note_blocks:
        comment_lines.append(f"{indent}#")
        comment_lines.append(f"{indent}# @par Note")
        for block in note_blocks:
            comment_lines.append(f"{indent}# {_sanitize_text(block)}".rstrip())

    see_also_blocks = _render_blocks(sections.get("See Also", []))
    if see_also_blocks:
        for block in see_also_blocks:
            comment_lines.append(f"{indent}#")
            comment_lines.append(f"{indent}# @see {_sanitize_text(block.removeprefix('- ').strip())}".rstrip())

    return [f"{line}\n" for line in comment_lines]


def _docstring_expr(node: Module | ClassDef | FunctionDef | AsyncFunctionDef) -> Expr | None:
    if not getattr(node, "body", None):
        return None
    first = node.body[0]
    if isinstance(first, Expr) and isinstance(first.value, Constant) and isinstance(first.value.value, str):
        return first
    return None


def _def_line(node: ClassDef | FunctionDef | AsyncFunctionDef) -> int:
    if node.decorator_list:
        return min(decorator.lineno for decorator in node.decorator_list)
    return node.lineno


def _rewrite_placeholder(
    node: Module | ClassDef | FunctionDef | AsyncFunctionDef,
    doc_expr: Expr,
) -> list[str]:
    if isinstance(node, Module):
        return []
    if len(node.body) == 1:
        return [f"{' ' * doc_expr.col_offset}pass  # Docstring moved to Doxygen comments.\n"]
    return []


def transform_python_for_doxygen(source: str) -> str:
    """Rewrite Python docstrings into Doxygen-style comments."""
    tree = parse(source)
    lines = source.splitlines(keepends=True)
    inserts: dict[int, list[str]] = defaultdict(list)
    replacements: dict[int, SourceEdit] = {}

    def visit(node: Module | ClassDef | FunctionDef | AsyncFunctionDef) -> None:
        doc_expr = _docstring_expr(node)
        if doc_expr is not None:
            docstring = get_docstring(node, clean=True) or ""
            if isinstance(node, Module):
                indent = ""
                insert_line = doc_expr.lineno
            else:
                indent = " " * node.col_offset
                insert_line = _def_line(node)

            comment_lines = _build_comment_lines(docstring, indent)
            if comment_lines:
                inserts[insert_line].extend(comment_lines)

            replacements[doc_expr.lineno] = SourceEdit(
                start_line=doc_expr.lineno,
                end_line=doc_expr.end_lineno or doc_expr.lineno,
                replacement=_rewrite_placeholder(node, doc_expr),
            )

        for child in getattr(node, "body", []):
            if isinstance(child, (ClassDef, FunctionDef, AsyncFunctionDef)):
                visit(child)

    visit(tree)

    output: list[str] = []
    line_no = 1
    while line_no <= len(lines):
        if line_no in inserts:
            output.extend(inserts[line_no])

        replacement = replacements.get(line_no)
        if replacement is not None:
            output.extend(replacement.replacement)
            line_no = replacement.end_line + 1
            continue

        output.append(lines[line_no - 1])
        line_no += 1

    return "".join(output)
