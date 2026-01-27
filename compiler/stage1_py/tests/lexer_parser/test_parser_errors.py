#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from conftest import has_error_code


def test_parser_reserved_variable_names(analyze_single):
    src = """
    module main;

    func main() -> int {
        let uint: int = 0;
        return uint;
    }
    """
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0010")

    src = """
    module main;

    func main() -> int {
        let int: int = 0;
        return int;
    }
    """
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0011")


def test_parser_unexpected_top_level_token(analyze_single):
    result = analyze_single("main", "module main; +;")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0020")


def test_parser_unexpected_pattern_token(analyze_single):
    src = """
    module main;

    enum Option { None; Some(value: int); }

    func main(opt: Option) -> int {
        match (opt) {
            123 => { return 0; }
        }
    }
    """
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0182")
