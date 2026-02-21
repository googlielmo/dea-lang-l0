"""
Tests for cast expressions and nullability type checking.
"""

#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

import pytest

from conftest import has_error_code


@pytest.mark.parametrize(
    "src",
    [
        """
        module main;

        func f() -> int {
            return "hello" as int;
        }
        """,
        """
        module main;

        func f() -> string {
            return 42 as string;
        }
        """,
        """
        module main;

        func f(x: bool) -> int {
            return x as int;
        }
        """,
    ],
)
def test_invalid_casts_rejected(src, analyze_single):
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0230")


def test_null_assignment_to_non_nullable_fails(analyze_single):
    src = """
    module main;

    func f() -> int {
        let x: int = null;
        return x;
    }
    """

    result = analyze_single("main", src)
    assert result.has_errors()
    assert any("type mismatch" in d.message for d in result.diagnostics)


def test_try_operator_rejected_on_non_nullable(analyze_single):
    src = """
    module main;

    func g(y: int) -> int {
        return y?;
    }
    """

    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0250")


def test_assign_non_nullable_into_nullable_does_not_require_cast(analyze_single):
    src = """
    module main;

    func h(a: int) -> int {
        let b: int? = a;
        return 0;
    }
    """

    result = analyze_single("main", src)
    assert not result.has_errors()


def test_assign_nullable_into_non_nullable_requires_unwrap(analyze_single):
    src = """
    module main;

    func h(a: int?) -> int {
        let b: int = a;
        return b;
    }
    """

    result = analyze_single("main", src)
    assert result.has_errors()
    assert any("type mismatch" in d.message for d in result.diagnostics)


def test_rt_string_release_rejects_optional_string(analyze_single):
    src = """
    module main;
    import sys.rt;

    func f(s: string?) -> void {
        rt_string_release(s);
    }
    """

    result = analyze_single("main", src)
    assert result.has_errors()
    assert any("expected 'string', got 'string?'" in d.message for d in result.diagnostics)
