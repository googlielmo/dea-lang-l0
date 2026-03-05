# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
"""Normalize native Doxygen LaTeX output for L0 sources."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .l0_docgen_l0_helpers import extract_l0_enum_variants, module_name_for_source_path

_POINTER_MACRO = r"\texorpdfstring{$\ast$}{*}"
_ARROW_MACRO = r"\texorpdfstring{$\rightarrow$}{->}"


def _escape_latex_texttt(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "_": r"\_",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _normalize_signature_line(line: str) -> str:
    if not any(marker in line for marker in ("func ", "struct ", r"\item[{", ":")):
        return line
    normalized = re.sub(r":(?:\\\+)+", ": ", line)
    normalized = re.sub(r"\s+" + re.escape(_POINTER_MACRO), lambda _: _POINTER_MACRO, normalized)
    if r"\hspace{0.3cm}{\ttfamily [extern]}" in normalized and "func " in normalized:
        normalized = normalized.replace(r"\hspace{0.3cm}{\ttfamily [extern]}", "")
        normalized = re.sub(r"(?<!\S)func\s+", "extern func ", normalized, count=1)
    return normalized


def _normalize_prose_arrow_line(line: str) -> str:
    normalized = line.replace(r"-\/\texorpdfstring{$>$}{>}", _ARROW_MACRO)
    normalized = normalized.replace(r"-\/$>$", _ARROW_MACRO)
    normalized = normalized.replace(r"\texorpdfstring{\textrightarrow}{->}", _ARROW_MACRO)
    return normalized


def _insert_after_index(text: str, block: str) -> str:
    if block in text:
        return text
    match = re.search(r"(\\index\{[^\n]+\}\n)", text)
    if match is None:
        return text
    return text[: match.end()] + "\n" + block.rstrip() + "\n" + text[match.end() :]


def _normalize_public_attributes_section(text: str) -> str:
    start = text.find(r"\doxysubsubsection*{Public Attributes}")
    if start == -1:
        return text
    end = text.find(r"\doxysubsection{Detailed Description}", start)
    if end == -1:
        return text

    lines = text[start:end].splitlines()
    for index, line in enumerate(lines[:-1]):
        if line.strip() != r"\item":
            continue
        candidate = lines[index + 1]
        stripped = candidate.strip()
        if not stripped:
            continue
        match = re.match(r"^(?P<type>.+?)\s+(?P<name>\\doxymbox\{.+\}|[^\s]+)$", stripped)
        if match is None:
            continue
        indent = candidate[: len(candidate) - len(candidate.lstrip())]
        lines[index + 1] = indent + _normalize_signature_line(f"{match.group('name')}: {match.group('type')}")

    return text[:start] + "\n".join(lines) + text[end:]


def _normalize_member_data_signatures(text: str) -> str:
    pattern = re.compile(
        r"^(?P<indent>\s*)(?P<type>.+?)\s+[A-Za-z0-9\\+._]+::(?:\\\+)?(?P<name>.+)\}$",
        re.MULTILINE,
    )

    def replace(match: re.Match[str]) -> str:
        line = f"{match.group('name')}: {match.group('type')}}}"
        return match.group("indent") + _normalize_signature_line(line)

    return pattern.sub(replace, text)


def _normalize_tex_lines(text: str) -> str:
    normalized_lines = []
    for line in text.splitlines():
        line = _normalize_signature_line(line)
        line = _normalize_prose_arrow_line(line)
        normalized_lines.append(line)
    return "\n".join(normalized_lines) + "\n"


def _normalize_prose_arrows(text: str) -> str:
    return "\n".join(_normalize_prose_arrow_line(line) for line in text.splitlines()) + "\n"


def _normalize_l0_signature_links(text: str) -> str:
    pattern = re.compile(
        r"extern func \\(?P<kind>hyper|doxy)link\{(?P<target>[^}]+)\}\{(?P<label>[^}]*)\}"
        r"(?P<args>\([^)]*\))?\s*"
        + re.escape(_ARROW_MACRO)
        + r"\s*(?P<ret>[^;{}]+);"
    )

    def replace(match: re.Match[str]) -> str:
        label = match.group("label").strip()
        args = (match.group("args") or "").strip()
        ret = match.group("ret").strip()
        if args and "(" not in label:
            label = f"{label}{args}"
        link_label = f"func {label} {_ARROW_MACRO} {ret}"
        return rf"extern \{match.group('kind')}link{{{match.group('target')}}}{{{link_label}}};"

    return pattern.sub(replace, text)


def _normalize_link_display_name(text: str) -> str:
    normalized = text.replace(r"\+", "").replace(r"\_", "_")
    normalized = normalized.replace("{", "").replace("}", "")
    return normalized.strip()


def _retarget_l0_symbol_links(text: str, preferred_refids_by_name: dict[str, str]) -> str:
    pattern = re.compile(r"\\(?P<kind>hyper|doxy)link\{(?P<target>[^}]+)\}\{(?P<label>[^}]*)\}")

    def replace(match: re.Match[str]) -> str:
        target = match.group("target")
        if not target.startswith("classl0__"):
            return match.group(0)

        label = match.group("label")
        normalized_label = _normalize_link_display_name(label)
        if "." in normalized_label or normalized_label.startswith("l0_"):
            return match.group(0)

        preferred_target = preferred_refids_by_name.get(normalized_label)
        if not preferred_target or preferred_target == target:
            return match.group(0)

        return rf"\{match.group('kind')}link{{{preferred_target}}}{{{label}}}"

    return pattern.sub(replace, text)


def _variants_block(variants: list[str]) -> list[str]:
    lines = [r"\textbf{Variants:}\\", r"\begin{DoxyItemize}"]
    lines.extend(rf"\item \texttt{{{_escape_latex_texttt(variant)}}}" for variant in variants)
    lines.append(r"\end{DoxyItemize}")
    lines.append("")
    return lines


def _inject_enum_variants(text: str, file_compound: ET.Element) -> str:
    lines = text.splitlines()
    insertions: list[tuple[int, list[str]]] = []
    removals: list[tuple[int, int]] = []

    for section in file_compound.findall("sectiondef"):
        for memberdef in section.findall("memberdef"):
            if memberdef.attrib.get("kind") != "enum":
                continue
            source_variants = extract_l0_enum_variants(memberdef)
            if not source_variants:
                continue
            xml_variants = [
                enumvalue.findtext("name", default="").strip()
                for enumvalue in memberdef.findall("enumvalue")
                if enumvalue.findtext("name", default="").strip()
            ]
            if source_variants == xml_variants:
                continue

            name = memberdef.findtext("name", default="").strip()
            if not name:
                continue

            header_index = next(
                (idx for idx, line in enumerate(lines) if line.startswith(r"\doxysubsubsection") and f"{{{name}}}{{{name}}}" in line),
                None,
            )
            if header_index is None:
                continue

            enum_fields_index = next(
                (idx for idx in range(header_index, len(lines)) if lines[idx].startswith(r"\begin{DoxyEnumFields}")),
                None,
            )
            if enum_fields_index is None:
                continue

            enum_fields_end = next(
                (idx for idx in range(enum_fields_index, len(lines)) if lines[idx].startswith(r"\end{DoxyEnumFields}")),
                None,
            )
            if enum_fields_end is None:
                continue

            removals.append((enum_fields_index, enum_fields_end + 1))

            if any(
                line.startswith(r"\paragraph{Variants}") or line.startswith(r"\textbf{Variants:}\\")
                for line in lines[header_index:enum_fields_index]
            ):
                continue

            insertions.append((enum_fields_index, _variants_block(source_variants)))

    for start, end in reversed(removals):
        del lines[start:end]

    for insert_index, block in reversed(insertions):
        lines[insert_index:insert_index] = block

    return "\n".join(lines) + "\n"


def _normalize_file_tex(text: str, file_compound: ET.Element, preferred_refids_by_name: dict[str, str]) -> str:
    source_path = file_compound.find("location").attrib["file"]
    module_name = module_name_for_source_path(source_path)
    normalized = _normalize_tex_lines(text)
    normalized = _inject_enum_variants(normalized, file_compound)
    normalized = _retarget_l0_symbol_links(normalized, preferred_refids_by_name)
    if module_name:
        normalized = _insert_after_index(
            normalized,
            rf"\textbf{{Module:}} \texttt{{{_escape_latex_texttt(module_name)}}}\par\medskip",
        )
    return normalized


def _normalize_symbol_tex(
    text: str,
    compounddef: ET.Element,
    preferred_refids_by_name: dict[str, str],
) -> str:
    normalized = _normalize_tex_lines(text)
    normalized = _normalize_public_attributes_section(normalized)
    normalized = _normalize_member_data_signatures(normalized)
    normalized = _retarget_l0_symbol_links(normalized, preferred_refids_by_name)
    return normalized


def normalize_latex_site(xml_dir: Path, latex_dir: Path) -> None:
    """Normalize native Doxygen LaTeX output for L0 sources."""
    if not latex_dir.exists():
        return

    file_compounds_by_source: dict[str, ET.Element] = {}
    file_refids_by_source: dict[str, str] = {}
    preferred_refids_by_name: dict[str, str] = {}
    symbol_compounds: list[ET.Element] = []

    for xml_path in sorted(xml_dir.glob("*.xml")):
        if xml_path.name == "index.xml":
            continue
        root = ET.parse(xml_path).getroot()
        compounddef = root.find("compounddef")
        if compounddef is None:
            continue
        location = compounddef.find("location")
        source_path = location.attrib.get("file", "") if location is not None else ""
        if not source_path or Path(source_path).is_absolute() or Path(source_path).suffix != ".l0":
            continue
        kind = compounddef.attrib.get("kind", "")
        if kind == "file":
            file_compounds_by_source[source_path] = compounddef
            file_refids_by_source[source_path] = compounddef.attrib["id"]
            for section in compounddef.findall("sectiondef"):
                for memberdef in section.findall("memberdef"):
                    if memberdef.attrib.get("kind") == "enum":
                        name = memberdef.findtext("name", default="").strip()
                        refid = memberdef.attrib.get("id", "")
                        if name and refid:
                            preferred_refids_by_name.setdefault(name, refid)
        elif kind in {"struct", "union", "class"}:
            name = compounddef.findtext("compoundname", default="").strip()
            if name:
                preferred_refids_by_name.setdefault(name, compounddef.attrib["id"])
            symbol_compounds.append(compounddef)

    for source_path, file_compound in file_compounds_by_source.items():
        tex_path = latex_dir / f"{file_compound.attrib['id']}.tex"
        if not tex_path.exists():
            continue
        tex_path.write_text(
            _normalize_file_tex(tex_path.read_text(encoding="utf-8"), file_compound, preferred_refids_by_name),
            encoding="utf-8",
        )

    for compounddef in symbol_compounds:
        source_path = compounddef.find("location").attrib["file"]
        file_refid = file_refids_by_source.get(source_path)
        if not file_refid:
            continue
        tex_path = latex_dir / f"{compounddef.attrib['id']}.tex"
        if not tex_path.exists():
            continue
        tex_path.write_text(
            _normalize_symbol_tex(tex_path.read_text(encoding="utf-8"), compounddef, preferred_refids_by_name),
            encoding="utf-8",
        )

    for tex_path in sorted(latex_dir.glob("*.tex")):
        tex = tex_path.read_text(encoding="utf-8")
        tex = _normalize_prose_arrows(tex)
        tex = _normalize_l0_signature_links(tex)
        tex_path.write_text(tex, encoding="utf-8")
