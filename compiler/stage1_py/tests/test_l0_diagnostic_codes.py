#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from conftest import has_error_code
from l0_diagnostics import DIAGNOSTIC_CODE_FAMILIES
from l0_driver import L0Driver


LEX_TRIGGERS = {
    "LEX-0010": '"unterminated',
    "LEX-0020": "'",
    "LEX-0021": "'a",
    "LEX-0030": "'\\u0100'",
    "LEX-0040": "@",
    "LEX-0050": '"\\xGG"',
    "LEX-0051": '"\\u12"',
    "LEX-0052": '"\\U1234567"',
    "LEX-0053": '"\\777"',
    "LEX-0059": '"\\q"',
    "LEX-0060": "2147483648",
    "LEX-0070": "/* unterminated",
}

PAR_TRIGGERS = {
    "PAR-0010": dedent(
        """
        module main;

        func main() -> int {
            let uint: int = 0;
            return 0;
        }
        """
    ),
    "PAR-0011": dedent(
        """
        module main;

        func main() -> int {
            let int: int = 0;
            return 0;
        }
        """
    ),
    "PAR-0020": "module main; +;",
    "PAR-0041": "module main; func () -> int { return 0; }",
    "PAR-0045": "module main; func foo(a: int -> int { return a; }",
    "PAR-0053": "module main; struct Point { : int; }",
    "PAR-0055": "module main; struct Point { x: int }",
    "PAR-0063": "module main; enum Option { ; }",
    "PAR-0067": "module main; enum Option { None }",
    "PAR-0082": "module main; let x: int 1;",
    "PAR-0083": "module main; let x: int = 1",
    "PAR-0122": "module main; func main() -> int { if (true { return 1; } }",
    "PAR-0132": "module main; func main() -> int { while (true { return 1; } }",
    "PAR-0142": "module main; func main() -> int { for (let i: int = 0 i < 3; i = i + 1) { return 0; } }",
    "PAR-0143": "module main; func main() -> int { for (let i: int = 0; i < 3 i = i + 1) { return 0; } }",
    "PAR-0174": "module main; enum Option { None; } func main(opt: Option) -> int { match (opt) { None { return 0; } } }",
    "PAR-0176": "module main; enum Option { None; } func main(opt: Option) -> int { match (opt) { None => { return 0; } None => { return 1; } } }",
    "PAR-0177": "module main; enum Option { None; } func main(opt: Option) -> int { match (opt) { } }",
    "PAR-0182": "module main; enum Option { None; } func main(opt: Option) -> int { match (opt) { 123 => { return 0; } } }",
    "PAR-0210": "module main; func add(a: int, b: int) -> int { return a + b; } func main() -> int { return add(1, 2; }",
    "PAR-0211": "module main; func main() -> int { let v: int = arr[0; return v; }",
    "PAR-0224": "module main; func main() -> int { let x: int = (1 + 2; return x; }",
    "PAR-0225": "module main; func main() -> int { let x: int = ; return 0; }",
    "PAR-0310": "import std.io;",
    "PAR-0311": "module ;",
    "PAR-0312": "module main\nfunc main() -> int { return 0; }",
    "PAR-0320": "module main; import ;",
    "PAR-0321": "module main; import std.io",
    "PAR-0400": "module main; type Alias = ;",
    "PAR-9401": "module main; func main() -> int { let x: int[] = 0; return x; }",
}

DRV_TRIGGERS = {
    "DRV-0010": "missing-file",
    "DRV-0020": "module-mismatch",
    "DRV-0030": "import-cycle",
}


def _all_codes() -> list[str]:
    codes: list[str] = []
    for family in DIAGNOSTIC_CODE_FAMILIES.values():
        codes.extend(family)
    return codes


def _analyze_with_driver(tmp_path: Path, mode: str):
    driver = L0Driver()
    driver.search_paths.add_project_root(tmp_path)

    if mode == "missing-file":
        return driver.analyze("missing")

    if mode == "module-mismatch":
        (tmp_path / "foo.l0").write_text("module bar;\n")
        return driver.analyze("foo")

    if mode == "import-cycle":
        (tmp_path / "a.l0").write_text("module a;\nimport b;\n")
        (tmp_path / "b.l0").write_text("module b;\nimport a;\n")
        return driver.analyze("a")

    raise ValueError(f"unknown driver trigger mode: {mode}")


@pytest.mark.parametrize("code", _all_codes())

def test_diagnostic_code_triggers(code, analyze_single, tmp_path):
    if code in DRV_TRIGGERS:
        result = _analyze_with_driver(tmp_path, DRV_TRIGGERS[code])
        assert result.has_errors()
        assert has_error_code(result.diagnostics, code)
        return

    if code in LEX_TRIGGERS:
        result = analyze_single("main", LEX_TRIGGERS[code])
        assert result.has_errors()
        assert has_error_code(result.diagnostics, code)
        return

    if code in PAR_TRIGGERS:
        result = analyze_single("main", PAR_TRIGGERS[code])
        assert result.has_errors()
        assert has_error_code(result.diagnostics, code)
        return

    pytest.xfail("TODO: add minimal trigger for this diagnostic code")
