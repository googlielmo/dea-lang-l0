# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
"""Generate HTML, Markdown, and LaTeX API documentation."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .l0_docgen_l0_filter import transform_l0_for_doxygen
from .l0_docgen_latex import normalize_latex_site
from .l0_docgen_markdown import (
    normalize_search_result_urls,
    render_compat_redirect_pages,
    render_curated_html_site,
    render_markdown_site,
    render_raw_reference_backlinks,
    rewrite_and_prune_raw_html_surface,
)
from .l0_docgen_python_filter import transform_python_for_doxygen


@dataclass(frozen=True)
class SourceManifest:
    """Manifest of sources included in API documentation."""

    files: list[Path]


def repo_root() -> Path:
    """Return the repository root."""
    return Path(__file__).resolve().parents[2]


def build_source_manifest(root: Path) -> SourceManifest:
    """Return the exact list of sources included in generated API docs."""
    files: list[Path] = []

    for path in sorted((root / "compiler/stage1_py").rglob("*.py")):
        rel = path.relative_to(root)
        if "tests" in rel.parts or "__pycache__" in rel.parts:
            continue
        files.append(rel)

    for path in sorted((root / "compiler/stage2_l0/src").rglob("*.l0")):
        files.append(path.relative_to(root))

    files.append(Path("compiler/stage2_l0/check_trace_log.py"))

    for path in sorted((root / "compiler/shared/l0/stdlib").rglob("*.l0")):
        files.append(path.relative_to(root))

    for path in sorted((root / "compiler/shared/runtime").glob("*.h")):
        files.append(path.relative_to(root))

    return SourceManifest(files=sorted(set(files)))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html-only", action="store_true", help="Generate only HTML output.")
    parser.add_argument("--markdown-only", action="store_true", help="Generate only Markdown output.")
    parser.add_argument("--latex-only", action="store_true", help="Generate only LaTeX output.")
    parser.add_argument("--no-latex", action="store_true", help="Skip LaTeX generation in the default mixed mode.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/docs"),
        help="Output root for generated documentation.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on Doxygen warnings and synthetic __padN__ symbol regressions.",
    )
    args = parser.parse_args(argv)
    only_modes = [args.html_only, args.markdown_only, args.latex_only]
    if sum(1 for enabled in only_modes if enabled) > 1:
        parser.error("--html-only, --markdown-only, and --latex-only are mutually exclusive")
    if args.no_latex and any(only_modes):
        parser.error("--no-latex cannot be combined with --html-only, --markdown-only, or --latex-only")
    return args


def _resolve_output_modes(args: argparse.Namespace) -> tuple[bool, bool, bool]:
    if args.html_only:
        return True, False, False
    if args.markdown_only:
        return False, True, False
    if args.latex_only:
        return False, False, True
    return True, True, not args.no_latex


def _copy_regular_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _build_shadow_tree(root: Path, manifest: SourceManifest, shadow_root: Path) -> None:
    if shadow_root.exists():
        shutil.rmtree(shadow_root)
    shadow_root.mkdir(parents=True)

    for relative_path in manifest.files:
        src = root / relative_path
        dst = shadow_root / relative_path
        if src.suffix == ".py":
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(transform_python_for_doxygen(src.read_text(encoding="utf-8")), encoding="utf-8")
        elif src.suffix == ".l0":
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(transform_l0_for_doxygen(src.read_text(encoding="utf-8")), encoding="utf-8")
        else:
            _copy_regular_file(src, dst)


def _write_template(template_name: str, destination: Path, **context: object) -> None:
    templates_dir = repo_root() / "scripts/docs/templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    destination.write_text(env.get_template(template_name).render(**context), encoding="utf-8")


def _patch_mcss_renderer(mcss_root: Path) -> None:
    renderer = mcss_root / "documentation/doxygen.py"
    text = renderer.read_text(encoding="utf-8")
    replacements = {
        "title = html.escape(i.text)": 'title = html.escape("".join(i.itertext()))',
        "if not i.text:": "if not i.text and len(i) == 0:",
        "html.escape(i.text))": 'html.escape("".join(i.itertext())))',
        "if compounddef.attrib.get('language', 'C++') not in ['C++']:": "if compounddef.attrib.get('language', 'C++') not in ['C++', 'Python', 'C', 'Markdown', 'Objective-C']:",
        "if not state.config['SEARCH_DISABLED'] and not compound.kind == 'example' and (compound.kind == 'group' or compound.brief or len(compounddef.find('detaileddescription'))):": (
            "if not state.config['SEARCH_DISABLED'] and compound.kind != 'dir' and not compound.kind == 'example' and "
            "(compound.kind == 'group' or compound.brief or len(compounddef.find('detaileddescription'))):"
        ),
        "        return (html.escape('<{}>'.format(make_include_strip_from_path(file, state.doxyfile['STRIP_FROM_INC_PATH']) if state.doxyfile['STRIP_FROM_INC_PATH'] is not None else file)), state.compounds[state.includes[file]].url)": (
            "        include_name = make_include_strip_from_path(file, state.doxyfile['STRIP_FROM_INC_PATH']) if state.doxyfile['STRIP_FROM_INC_PATH'] is not None else file\n"
            "        if include_name.endswith(('.l0', '.py')):\n"
            "            rendered_include = include_name\n"
            "        else:\n"
            "            rendered_include = '<{}>'.format(include_name)\n"
            "        return (html.escape(rendered_include), state.compounds[state.includes[file]].url)"
        ),
        "        return (html.escape('<{}>'.format(name)), state.compounds[file_id].url)": (
            "        if name.endswith(('.l0', '.py')):\n"
            "            rendered_include = name\n"
            "        else:\n"
            "            rendered_include = '<{}>'.format(name)\n"
            "        return (html.escape(rendered_include), state.compounds[file_id].url)"
        ),
    }
    updated = text
    for old, new in replacements.items():
        updated = updated.replace(old, new)
    if updated != text:
        renderer.write_text(updated, encoding="utf-8")


def _run_command(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def _warnings_count(warnings_log: Path) -> int:
    if not warnings_log.exists():
        return 0
    ignore_patterns = [
        re.compile(r"Failed to map file extension 'md'"),
        re.compile(r"Found documentation for module .* but it has no primary interface unit"),
        re.compile(r"argument '.*' of command @param is not found in the argument list of"),
        re.compile(r"the name 'Optional' supplied as the argument of the \\class"),
        re.compile(r"the name 'Base' supplied as the argument of the \\class"),
    ]
    count = 0
    for line in warnings_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if any(pattern.search(line) for pattern in ignore_patterns):
            continue
        count += 1
    return count


def _find_synthetic_pad_members(xml_dir: Path) -> list[tuple[str, str]]:
    """Return synthetic __padN__ members discovered in generated Doxygen XML."""
    pad_member_re = re.compile(r"^__pad[0-9]+__$")
    hits: list[tuple[str, str]] = []
    for xml_path in sorted(xml_dir.glob("*.xml")):
        if xml_path.name == "Doxyfile.xml":
            continue
        root = ET.parse(xml_path).getroot()
        for name_node in root.findall(".//memberdef/name"):
            name = (name_node.text or "").strip()
            if pad_member_re.fullmatch(name):
                hits.append((xml_path.name, name))
    return hits


def _normalize_html_output(doxygen_root: Path, html_dir: Path) -> None:
    generated_html_dir = doxygen_root / "html"
    if not generated_html_dir.exists():
        return
    if html_dir.exists():
        shutil.rmtree(html_dir)
    shutil.copytree(generated_html_dir, html_dir)


def main(argv: list[str] | None = None) -> int:
    """Run the docs pipeline."""
    args = parse_args(argv)
    root = repo_root()
    html_enabled, markdown_enabled, latex_enabled = _resolve_output_modes(args)
    output_root = (root / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir.resolve()
    doxygen_root = output_root / "doxygen"
    xml_dir = doxygen_root / "xml"
    html_dir = output_root / "html"
    markdown_dir = output_root / "markdown"
    tmp_root = output_root / ".tmp"
    shadow_root = tmp_root / "shadow"
    generated_root = tmp_root / "generated"
    templates_dir = root / "scripts/docs/templates"
    xml_warnings_log = doxygen_root / "warnings-xml.log"
    latex_warnings_log = doxygen_root / "warnings-latex.log"
    xml_doxygen_path = generated_root / "Doxyfile.xml"
    latex_doxygen_path = generated_root / "Doxyfile.latex"
    mcss_conf_path = generated_root / "mcss_conf.py"
    html_mainpage_path = shadow_root / "docs-mainpage-html.md"
    latex_mainpage_path = shadow_root / "docs-mainpage-latex.md"
    mcss_root = root / "tools/m.css"

    if not shutil.which("doxygen"):
        raise SystemExit("doxygen was not found in PATH")
    if not mcss_root.is_dir():
        raise SystemExit(f"vendored m.css checkout not found at {mcss_root}")

    if output_root.exists():
        shutil.rmtree(output_root)
    xml_dir.mkdir(parents=True)
    if html_enabled:
        html_dir.mkdir(parents=True)
    if markdown_enabled:
        markdown_dir.mkdir(parents=True)
    generated_root.mkdir(parents=True)

    manifest = build_source_manifest(root)
    _build_shadow_tree(root, manifest, shadow_root)
    _patch_mcss_renderer(mcss_root)

    _write_template("mainpage_html.md.j2", html_mainpage_path)
    _write_template(
        "doxyfile.in",
        xml_doxygen_path,
        output_directory=doxygen_root.as_posix(),
        mainpage=html_mainpage_path.as_posix(),
        stage1_dir=(shadow_root / "compiler/stage1_py").as_posix(),
        stage2_src_dir=(shadow_root / "compiler/stage2_l0/src").as_posix(),
        stage2_cli_file=(shadow_root / "compiler/stage2_l0/check_trace_log.py").as_posix(),
        shared_stdlib_dir=(shadow_root / "compiler/shared/l0/stdlib").as_posix(),
        shared_runtime_dir=(shadow_root / "compiler/shared/runtime").as_posix(),
        strip_from_path=shadow_root.as_posix(),
        warn_logfile=xml_warnings_log.as_posix(),
        generate_xml="YES",
        generate_latex="NO",
    )
    _write_template(
        "mcss_conf.py.in",
        mcss_conf_path,
        doxygen_path=xml_doxygen_path.as_posix(),
        html_output=html_dir.as_posix(),
    )

    _run_command(["doxygen", str(xml_doxygen_path)], cwd=root)

    if latex_enabled:
        _write_template("mainpage_latex.md.j2", latex_mainpage_path)
        _write_template(
            "doxyfile.in",
            latex_doxygen_path,
            output_directory=doxygen_root.as_posix(),
            mainpage=latex_mainpage_path.as_posix(),
            stage1_dir=(shadow_root / "compiler/stage1_py").as_posix(),
            stage2_src_dir=(shadow_root / "compiler/stage2_l0/src").as_posix(),
            stage2_cli_file=(shadow_root / "compiler/stage2_l0/check_trace_log.py").as_posix(),
            shared_stdlib_dir=(shadow_root / "compiler/shared/l0/stdlib").as_posix(),
            shared_runtime_dir=(shadow_root / "compiler/shared/runtime").as_posix(),
            strip_from_path=shadow_root.as_posix(),
            warn_logfile=latex_warnings_log.as_posix(),
            generate_xml="NO",
            generate_latex="YES",
        )
        _run_command(["doxygen", str(latex_doxygen_path)], cwd=root)

    markdown_render_root: Path | None = None
    if markdown_enabled or html_enabled:
        markdown_render_root = markdown_dir if markdown_enabled else tmp_root / "markdown-html-source"
        markdown_render_root.mkdir(parents=True, exist_ok=True)

    if html_enabled:
        _run_command([sys.executable, str(mcss_root / "documentation/doxygen.py"), str(mcss_conf_path)], cwd=root)
        _normalize_html_output(doxygen_root, html_dir)
        normalize_search_result_urls(html_dir)
    if markdown_render_root is not None:
        render_markdown_site(xml_dir, markdown_render_root, templates_dir)
    if html_enabled and markdown_render_root is not None:
        render_curated_html_site(xml_dir, markdown_render_root, html_dir, templates_dir)
        render_raw_reference_backlinks(xml_dir, markdown_render_root, html_dir)
        rewrite_and_prune_raw_html_surface(xml_dir, markdown_render_root, html_dir)
        render_compat_redirect_pages(xml_dir, markdown_render_root, html_dir, templates_dir)
    if latex_enabled:
        normalize_latex_site(xml_dir, doxygen_root / "latex")

    warning_count = _warnings_count(xml_warnings_log) + _warnings_count(latex_warnings_log)
    if args.strict:
        pad_hits = _find_synthetic_pad_members(xml_dir)
        if pad_hits:
            preview = ", ".join(f"{xml}:{name}" for xml, name in pad_hits[:8])
            raise SystemExit(
                "detected synthetic Doxygen members matching __padN__: "
                f"{preview}; this indicates an L0 parsing regression"
            )
    if args.strict and warning_count:
        raise SystemExit(
            "doxygen reported "
            f"{warning_count} warning(s); see {xml_warnings_log} and {latex_warnings_log}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
