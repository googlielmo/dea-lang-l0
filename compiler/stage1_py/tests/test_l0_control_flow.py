"""
Tests for control flow edge cases: break/continue validation and loop codegen.
"""

#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from conftest import has_error_code


# ============================================================================
# Break/continue outside loop detection
# ============================================================================


def test_typechecker_break_outside_loop(analyze_single):
    """Test that break outside loop is rejected."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> int {
            break;
            return 0;
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0110")


def test_typechecker_continue_outside_loop(analyze_single):
    """Test that continue outside loop is rejected."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> int {
            continue;
            return 0;
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0120")


def test_break_inside_while_loop_ok(analyze_single):
    """Test that break inside while loop is accepted."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> int {
            while (true) {
                break;
            }
            return 0;
        }
        """,
    )

    assert not result.has_errors()


def test_continue_inside_while_loop_ok(analyze_single):
    """Test that continue inside while loop is accepted."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> int {
            let i: int = 0;
            while (i < 10) {
                i = i + 1;
                continue;
            }
            return i;
        }
        """,
    )

    assert not result.has_errors()


def test_break_inside_for_loop_ok(analyze_single):
    """Test that break inside for loop is accepted."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> int {
            for (let i: int = 0; i < 10; i = i + 1) {
                break;
            }
            return 0;
        }
        """,
    )

    assert not result.has_errors()


def test_continue_inside_for_loop_ok(analyze_single):
    """Test that continue inside for loop is accepted."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> int {
            for (let i: int = 0; i < 10; i = i + 1) {
                continue;
            }
            return 0;
        }
        """,
    )

    assert not result.has_errors()


# ============================================================================
# Nested loop break/continue
# ============================================================================


def test_codegen_nested_loop_break(codegen_single):
    """Test that break in nested loop generates correct C code."""
    c_code, diags = codegen_single(
        "main",
        """
        module main;
        func f() -> int {
            let result: int = 0;
            while (true) {
                while (true) {
                    result = 1;
                    break;
                }
                result = 2;
                break;
            }
            return result;
        }
        """,
    )

    if c_code is None:
        assert False, f"Analysis failed: {[d.message for d in diags]}"

    # Should have multiple break statements
    assert c_code.count("break;") >= 2


def test_break_in_nested_if_inside_loop(analyze_single):
    """Test break inside if inside loop is valid."""
    result = analyze_single(
        "main",
        """
        module main;
        func f(x: int) -> int {
            while (true) {
                if (x > 0) {
                    break;
                }
            }
            return x;
        }
        """,
    )

    assert not result.has_errors()


# ============================================================================
# For loop edge cases
# ============================================================================


def test_codegen_for_loop_empty_clauses(codegen_single):
    """Test for loop with all empty clauses generates correct C."""
    c_code, diags = codegen_single(
        "main",
        """
        module main;
        func f() -> int {
            for (;;) {
                break;
            }
            return 0;
        }
        """,
    )

    if c_code is None:
        assert False, f"Analysis failed: {[d.message for d in diags]}"

    # Should generate while(1) or for(;;) pattern
    assert "while" in c_code or "for" in c_code


def test_for_loop_only_condition(analyze_single):
    """Test for loop with only condition."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> int {
            let i: int = 0;
            for (; i < 10;) {
                i = i + 1;
            }
            return i;
        }
        """,
    )

    assert not result.has_errors()


def test_for_loop_only_init(analyze_single):
    """Test for loop with only init."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> int {
            for (let i: int = 0;;) {
                break;
            }
            return 0;
        }
        """,
    )

    assert not result.has_errors()


def test_for_loop_only_update(analyze_single):
    """Test for loop with only update."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> int {
            let i: int = 0;
            for (;; i = i + 1) {
                if (i >= 10) {
                    break;
                }
            }
            return i;
        }
        """,
    )

    assert not result.has_errors()