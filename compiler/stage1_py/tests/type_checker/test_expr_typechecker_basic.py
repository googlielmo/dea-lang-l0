"""
Basic expression type checker tests.
"""

#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from conftest import has_error_code

from l0_ast import FuncDecl, ReturnStmt
from l0_types import BuiltinType


def test_add_function_ok(analyze_single):
    result = analyze_single(
        "main",
        """
        module main;

        func add(a: int, b: int) -> int {
            return a + b;
        }
        """,
    )

    assert not result.has_errors()

    mod = result.cu.modules["main"]
    func = next(d for d in mod.decls if isinstance(d, FuncDecl) and d.name == "add")
    ret = next(s for s in func.body.stmts if isinstance(s, ReturnStmt))
    expr = ret.value

    t = result.expr_types[id(expr)]
    assert isinstance(t, BuiltinType)
    assert t.name == "int"


def test_call_wrong_arity(analyze_single):
    result = analyze_single(
        "main",
        """
        module main;

        func callee(x: int) -> int {
            return x;
        }

        func caller() -> int {
            return callee(1, 2);
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0183")


def test_return_wrong_type(analyze_single):
    result = analyze_single(
        "main",
        """
        module main;

        func f() -> int {
            return true;
        }
        """,
    )

    assert result.has_errors()
    assert any("type mismatch" in d.message for d in result.diagnostics)