"""Integration tests for L0 string equality and relational operators.

Covers type-check, codegen (lowering through ``rt_string_equals`` /
``rt_string_compare``), and end-to-end compile-and-run for ``==``, ``!=``,
``<``, ``<=``, ``>``, ``>=`` on ``string`` operands.
"""

#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

import pytest


@pytest.mark.parametrize("op", ["==", "!="])
def test_codegen_string_equality_uses_rt_helper(op, codegen_single):
    """String ==/!= lowers through rt_string_equals."""
    c_code, diags = codegen_single("main", f"""
        module main;
        func f(a: string, b: string) -> bool {{
            return a {op} b;
        }}
        func main() -> int {{ return 0; }}
    """)
    assert c_code is not None, [d.message for d in diags]
    assert "rt_string_equals" in c_code
    if op == "!=":
        assert "!rt_string_equals" in c_code or "!(rt_string_equals" in c_code


@pytest.mark.parametrize("op", ["<", "<=", ">", ">="])
def test_codegen_string_relational_uses_rt_compare(op, codegen_single):
    """String relational lowers through rt_string_compare."""
    c_code, diags = codegen_single("main", f"""
        module main;
        func f(a: string, b: string) -> bool {{
            return a {op} b;
        }}
        func main() -> int {{ return 0; }}
    """)
    assert c_code is not None, [d.message for d in diags]
    assert "rt_string_compare" in c_code
    assert f") {op} 0" in c_code


def test_string_equality_compiles_and_runs(codegen_single, compile_and_run, tmp_path):
    """Equal strings compare equal; distinct strings compare unequal."""
    c_code, diags = codegen_single("main", """
        module main;
        func main() -> int {
            let a: string = "hello";
            let b: string = "hello";
            let c: string = "world";
            if (!(a == b)) { return 1; }
            if (a != b) { return 2; }
            if (a == c) { return 3; }
            if (!(a != c)) { return 4; }
            return 0;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"string equality check failed: stderr={stderr}"


def test_string_relational_compiles_and_runs(codegen_single, compile_and_run, tmp_path):
    """Lexicographic ordering holds at runtime."""
    c_code, diags = codegen_single("main", """
        module main;
        func main() -> int {
            let a: string = "apple";
            let b: string = "banana";
            if (!(a < b)) { return 1; }
            if (!(a <= b)) { return 2; }
            if (!(b > a)) { return 3; }
            if (!(b >= a)) { return 4; }
            if (a > b) { return 5; }
            if (b < a) { return 6; }
            let c: string = "apple";
            if (!(a <= c)) { return 7; }
            if (!(a >= c)) { return 8; }
            if (a < c) { return 9; }
            if (a > c) { return 10; }
            return 0;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"string relational check failed: stderr={stderr}"
