#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from conftest import has_error_code
from l0_parser import Parser


def parse_module(src: str):
    parser = Parser.from_source(src)
    return parser.parse_module()


def test_parser_decls_valid_module_imports_and_defs():
    src = """
    module main;
    import std.io;
    import app.utils;

    struct Point {
        x: int;
        y: int;
    }

    enum Option {
        None;
        Some(value: int);
    }

    type Count = int;

    let zero: int = 0;

    func add(a: int, b: int) -> int {
        return a + b;
    }
    """
    mod = parse_module(src)

    assert mod.name == "main"
    assert [imp.name for imp in mod.imports] == ["std.io", "app.utils"]
    assert len(mod.decls) == 5


def test_parser_module_decl_errors(analyze_single):
    result = analyze_single("main", "module ;")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0311")

    result = analyze_single("main", "module main\nfunc main() -> int { return 0; }")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0312")


def test_parser_import_decl_errors(analyze_single):
    result = analyze_single("main", "module main; import ;")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0320")

    result = analyze_single("main", "module main; import std.io")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0321")


def test_parser_struct_decl_errors(analyze_single):
    result = analyze_single("main", "module main; struct Point { : int; }")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0053")

    result = analyze_single("main", "module main; struct Point { x: int }")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0055")


def test_parser_enum_decl_errors(analyze_single):
    result = analyze_single("main", "module main; enum Option { ; }")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0063")

    result = analyze_single("main", "module main; enum Option { None }")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0067")


def test_parser_func_decl_errors(analyze_single):
    result = analyze_single("main", "module main; func () -> int { return 0; }")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0041")

    result = analyze_single("main", "module main; func foo(a: int -> int { return a; }")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0045")


def test_parser_top_level_let_decl_errors(analyze_single):
    result = analyze_single("main", "module main; let x: int 1;")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0082")

    result = analyze_single("main", "module main; let x: int = 1")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "PAR-0083")
