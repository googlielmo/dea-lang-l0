#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from textwrap import dedent

from l0_driver import L0Driver


def _analyze_single(tmp_path, name: str, src: str):
    path = tmp_path / f"{name}.l0"
    path.write_text(dedent(src))

    driver = L0Driver()
    driver.search_paths.add_project_root(tmp_path)

    return driver.analyze(name)


def test_missing_enum_variant_rejected(tmp_path):
    src = """
    module main;

    enum Color { Red(); Green(); Blue(); }

    func f(c: Color) -> int {
        match (c) {
            Red() => { return 1; }
            Green() => { return 2; }
        }
    }
    """

    result = _analyze_single(tmp_path, "main", src)
    assert result.has_errors()


def test_unknown_variant_name_reports_error(tmp_path):
    src = """
    module main;

    enum Flag { On(); Off(); }

    func f(f: Flag) -> int {
        match (f) {
            Maybe() => { return 1; }
        }
    }
    """

    result = _analyze_single(tmp_path, "main", src)
    assert result.has_errors()
    msgs = "\n".join(d.message for d in result.diagnostics)
    assert "unknown variant" in msgs


def test_match_on_non_enum_type_rejected(tmp_path):
    src = """
    module main;

    func f(x: int) -> int {
        match (x) {
            _ => { return x; }
        }
    }
    """

    result = _analyze_single(tmp_path, "main", src)
    assert result.has_errors()
