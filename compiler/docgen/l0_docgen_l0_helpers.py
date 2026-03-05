# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
"""Shared L0 source helpers for docs generation."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path


def module_name_for_source_path(source_path: str) -> str | None:
    """Return the declared module name for an L0/Python source path."""
    path = Path(source_path)
    if path.suffix == ".l0" and not path.is_absolute() and path.exists():
        match = re.search(
            r"^\s*module\s+([A-Za-z_][A-Za-z0-9_.]*)\s*;",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if match:
            return match.group(1)
    if path.suffix in {".l0", ".py"}:
        return path.stem
    return None


def extract_l0_enum_variants(memberdef: ET.Element) -> list[str]:
    """Recover L0 enum variants from the original source body."""
    location = memberdef.find("location")
    if location is None:
        return []
    source_file = location.attrib.get("file", "")
    start_text = location.attrib.get("bodystart") or location.attrib.get("line")
    end_text = location.attrib.get("bodyend") or location.attrib.get("line")
    if not source_file or not start_text or not end_text:
        return []

    path = Path(source_file)
    if path.is_absolute() or not path.exists():
        return []

    try:
        start = int(start_text)
        end = int(end_text)
    except ValueError:
        return []

    if start <= 0 or end < start:
        return []

    variants: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines[start:end]:
        stripped = line.strip()
        if not stripped or stripped in {"{", "}"}:
            continue
        if stripped.startswith("//"):
            continue
        code = line.split("//", 1)[0].strip()
        if not code or code == "}":
            continue
        if code.endswith(";"):
            code = code[:-1].rstrip()
        if code:
            variants.append(code)
    return variants
