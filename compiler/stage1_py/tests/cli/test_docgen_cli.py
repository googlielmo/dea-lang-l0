# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
"""Tests for the docs CLI."""

from pathlib import Path

import pytest

from compiler.docgen.l0_docgen import _find_synthetic_pad_members, _patch_mcss_renderer, _resolve_output_modes, \
    parse_args, repo_root


def test_parse_args_defaults() -> None:
    args = parse_args([])
    assert args.output_dir == Path("build/docs")
    assert not args.html_only
    assert not args.markdown_only
    assert not args.latex_only
    assert not args.no_latex
    assert not args.strict
    assert _resolve_output_modes(args) == (True, True, True)


def test_parse_args_rejects_conflicting_output_modes() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--html-only", "--markdown-only"])
    with pytest.raises(SystemExit):
        parse_args(["--html-only", "--latex-only"])
    with pytest.raises(SystemExit):
        parse_args(["--markdown-only", "--latex-only"])


def test_parse_args_supports_latex_only_mode() -> None:
    args = parse_args(["--latex-only"])
    assert args.latex_only
    assert _resolve_output_modes(args) == (False, False, True)


def test_parse_args_supports_no_latex_mode() -> None:
    args = parse_args(["--no-latex"])
    assert args.no_latex
    assert _resolve_output_modes(args) == (True, True, False)


def test_parse_args_rejects_no_latex_with_only_modes() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--no-latex", "--html-only"])
    with pytest.raises(SystemExit):
        parse_args(["--no-latex", "--markdown-only"])
    with pytest.raises(SystemExit):
        parse_args(["--no-latex", "--latex-only"])


def test_find_synthetic_pad_members_detects_generated_padding_names(tmp_path: Path) -> None:
    (tmp_path / "with-pad.xml").write_text(
        """
<doxygen>
  <compounddef>
    <sectiondef>
      <memberdef kind="variable"><name>__pad0__</name></memberdef>
      <memberdef kind="variable"><name>real_field</name></memberdef>
    </sectiondef>
  </compounddef>
</doxygen>
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "without-pad.xml").write_text(
        """
<doxygen>
  <compounddef>
    <sectiondef>
      <memberdef kind="variable"><name>field_ok</name></memberdef>
    </sectiondef>
  </compounddef>
</doxygen>
""".strip()
        + "\n",
        encoding="utf-8",
    )

    assert _find_synthetic_pad_members(tmp_path) == [("with-pad.xml", "__pad0__")]


def test_find_synthetic_pad_members_ignores_non_matching_names(tmp_path: Path) -> None:
    (tmp_path / "candidates.xml").write_text(
        """
<doxygen>
  <compounddef>
    <sectiondef>
      <memberdef kind="variable"><name>__pad__</name></memberdef>
      <memberdef kind="variable"><name>__padA__</name></memberdef>
      <memberdef kind="variable"><name>__pad1_</name></memberdef>
      <memberdef kind="variable"><name>field</name></memberdef>
    </sectiondef>
  </compounddef>
</doxygen>
""".strip()
        + "\n",
        encoding="utf-8",
    )

    assert _find_synthetic_pad_members(tmp_path) == []


def test_mcss_template_uses_show_undocumented_setting() -> None:
    template = (repo_root() / "scripts/docs/templates/mcss_conf.py.in").read_text(encoding="utf-8")
    assert "SHOW_UNDOCUMENTED = True" in template
    assert "M_SHOW_UNDOCUMENTED" not in template
    assert "annotated.html" not in template


def test_patch_mcss_renderer_excludes_directory_pages_from_search_results(tmp_path: Path) -> None:
    mcss_root = tmp_path / "m.css"
    renderer_dir = mcss_root / "documentation"
    renderer_dir.mkdir(parents=True)
    renderer = renderer_dir / "doxygen.py"
    renderer.write_text(
        "if not state.config['SEARCH_DISABLED'] and not compound.kind == 'example' and "
        "(compound.kind == 'group' or compound.brief or len(compounddef.find('detaileddescription'))):\n"
        "    pass\n",
        encoding="utf-8",
    )

    _patch_mcss_renderer(mcss_root)

    patched = renderer.read_text(encoding="utf-8")
    assert "compound.kind != 'dir'" in patched
