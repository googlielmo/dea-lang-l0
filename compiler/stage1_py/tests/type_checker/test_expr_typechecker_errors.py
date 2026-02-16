"""
Tests for type checker error detection on invalid operator usage.
"""

#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from conftest import has_error_code


# ============================================================================
# Binary operator type errors
# ============================================================================


def test_typechecker_string_plus_int(analyze_single):
    """Test that string + int is rejected."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> string {
            return "a" + 1;
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0170")


def test_typechecker_bool_arithmetic(analyze_single):
    """Test that bool * bool is rejected."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> bool {
            return true * false;
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0170")


def test_typechecker_string_comparison_with_int(analyze_single):
    """Test that string < int is rejected."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> bool {
            return "a" < 1;
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0170")


# ============================================================================
# Unary operator type errors
# ============================================================================


def test_typechecker_unary_not_on_int(analyze_single):
    """Test that !int is rejected (logical not requires bool)."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> bool {
            return !42;
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0161")


def test_typechecker_unary_minus_on_bool(analyze_single):
    """Test that -bool is rejected (negation requires numeric type)."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> int {
            return -true;
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0160")


def test_typechecker_unary_minus_on_string(analyze_single):
    """Test that -string is rejected."""
    result = analyze_single(
        "main",
        """
        module main;
        func f() -> string {
            return -"hello";
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0160")