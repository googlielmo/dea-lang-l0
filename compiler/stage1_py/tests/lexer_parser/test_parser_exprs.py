#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from conftest import has_error_code


def test_parser_exprs_valid_operators_and_calls(analyze_single):
    src = """
    module main;

    func add(a: int, b: int) -> int {
        return a + b;
    }

    func main() -> int {
        let a: int = (1 + 2) * 3 - 4 / 2;
        let b: int = -a;
        let ok: bool = (a < 10) && (a != 0);
        let nope: bool = !ok || (a >= 2) || (a <= 5);
        let sum: int = add(a, 1);
        return sum;
    }
    """
    result = analyze_single("main", src)
    assert not result.has_errors()


def test_parser_expr_missing_paren_after_call(analyze_single):
    src = """
    module main;

    func add(a: int, b: int) -> int { return a + b; }

    func main() -> int {
        return add(1, 2;
    }
    """
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0210")


def test_parser_expr_missing_bracket_after_index(analyze_single):
    src = """
    module main;

    func main() -> int {
        let v: int = arr[0;
        return v;
    }
    """
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0211")


def test_parser_expr_missing_paren_after_group(analyze_single):
    src = """
    module main;

    func main() -> int {
        let x: int = (1 + 2;
        return x;
    }
    """
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0224")


def test_parser_expr_unexpected_token(analyze_single):
    src = """
    module main;

    func main() -> int {
        let x: int = ;
        return 0;
    }
    """
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0225")
