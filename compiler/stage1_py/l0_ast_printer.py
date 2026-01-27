#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

from dataclasses import is_dataclass, fields
from typing import List, Any

from l0_ast import Span, Node, Module


def _format_span(span: Span | None) -> str:
    if span is None:
        return ""
    return f" @{span.start_line}:{span.start_column}-{span.end_line}:{span.end_column}"


def format_node(node: Any, indent: int = 0) -> List[str]:
    """
    Generic, reflection-based AST pretty-printer.

    - Shows the node class name.
    - Prints simple scalar fields inline (excluding `span`).
    - Recursively prints child Node / list-of-Node fields on new indented lines.
    - Appends a concise span annotation like `@1:1-7:1` when available.
    """
    ind = "  " * indent

    # Lists: print each element at same indentation
    if isinstance(node, list):
        lines: List[str] = []
        for elem in node:
            lines.extend(format_node(elem, indent))
        return lines

    # AST nodes (dataclasses derived from Node)
    if isinstance(node, Node) and is_dataclass(node):
        span = node.span
        # Split fields into "simple scalars" vs "children"
        data_fields = [f for f in fields(node) if f.name != "span"]
        simple_parts = []
        child_fields = []

        for f in data_fields:
            value = getattr(node, f.name)
            if isinstance(value, Node) or isinstance(value, list):
                child_fields.append((f.name, value))
            else:
                simple_parts.append((f.name, value))

        # Header: ClassName(field1=..., field2=...) @line:col-line:col
        header = node.__class__.__name__
        if simple_parts:
            inner = ", ".join(f"{name}={value!r}" for name, value in simple_parts if value is not None)
            header = f"{header}({inner})"
        header += _format_span(span)

        lines: List[str] = [ind + header]

        # Child fields on separate indented lines
        for name, value in child_fields:
            if value is None:
                continue
            if isinstance(value, list):
                if not value:
                    continue
                lines.append(ind + "  " + f"{name}:")
                for elem in value:
                    lines.extend(format_node(elem, indent + 2))
            else:
                lines.append(ind + "  " + f"{name}:")
                lines.extend(format_node(value, indent + 2))

        return lines

    # Other dataclasses (if any) – fallback to repr
    if is_dataclass(node):
        return [ind + repr(node)]

    # Fallback for unexpected values
    return [ind + repr(node)]


def format_module(mod: Module) -> str:
    """
    Convenience: pretty-print a single Module as a string.
    """
    lines = format_node(mod, indent=0)
    return "\n".join(lines)
