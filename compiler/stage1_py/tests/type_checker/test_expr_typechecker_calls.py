"""
Tests for function call type checking.
"""

#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from conftest import has_error_code


def test_call_arity_errors(analyze_single):
    src = """
    module main;

    func foo(x: int) -> void { return; }

    func main() -> int {
        foo();
        foo(1, 2);
        return 0;
    }
    """

    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0183")


def test_call_argument_type_mismatch(analyze_single):
    src = """
    module main;

    func foo(x: int) -> void { return; }

    func main() -> int {
        foo("hi");
        return 0;
    }
    """

    result = analyze_single("main", src)
    assert result.has_errors()
    assert any("type mismatch" in d.message for d in result.diagnostics)
