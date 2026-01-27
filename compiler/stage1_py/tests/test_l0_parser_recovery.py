#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from conftest import has_error_code


def test_parser_recovery_stops_at_first_error(analyze_single):
    src = """
    module main;

    func first() -> int {
        let x: int = 1
        let y: int = ;
        return x;
    }

    func later() -> int {
        return 2;
    }
    """
    result = analyze_single("main", src)

    assert result.has_errors()
    assert result.cu is None
    assert len(result.diagnostics) == 1
    assert has_error_code(result.diagnostics, "PAR-0100")


def test_parser_recovery_import_error_blocks_later_decls(analyze_single):
    src = """
    module main;

    import std.io

    func ok() -> int {
        return 0;
    }

    func broken() -> int {
        let x: int = ;
        return x;
    }
    """
    result = analyze_single("main", src)

    assert result.has_errors()
    assert result.cu is None
    assert len(result.diagnostics) == 1
    assert has_error_code(result.diagnostics, "PAR-0321")
