#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

# test_l0_locals.py

from l0_ast import Module, Block, MatchStmt, IfStmt
from l0_locals import LocalScopeResolver, LocalKind
from l0_parser import Parser


def parse_module(src: str) -> Module:
    parser = Parser.from_source(src)
    mod = parser.parse_module()
    assert isinstance(mod, Module)
    return mod


def test_params_and_let_bindings_scopes():
    src = """
    module m;

    func f(a: int, b: int) -> int {
        let x: int = a;
        if (a < b) {
            let x: int = b;
            let y: int = x;
            return y;
        } else {
            let y: int = a;
            return y;
        }
    }
    """
    mod = parse_module(src)
    resolver = LocalScopeResolver({"m": mod})
    func_envs = resolver.resolve()

    f_env = func_envs[("m", "f")]
    root = f_env.root_scope

    # root scope contains parameters and top-level lets
    assert set(root.symbols.keys()) == {"a", "b", "x"}
    assert root.symbols["a"].kind is LocalKind.PARAM
    assert root.symbols["b"].kind is LocalKind.PARAM
    assert root.symbols["x"].kind is LocalKind.LOCAL

    body = f_env.func.body
    assert isinstance(body, Block)
    if_stmt = body.stmts[1]

    # then-block scope
    assert isinstance(if_stmt, IfStmt)
    assert isinstance(if_stmt.then_stmt, Block)
    then_scope = resolver.get_block_scope(if_stmt.then_stmt)
    assert then_scope is not None
    # 'x' is shadowed in then-block, 'y' is declared there
    assert set(then_scope.symbols.keys()) == {"x", "y"}
    assert then_scope.symbols["x"].kind is LocalKind.LOCAL
    assert then_scope.lookup("a") is not None  # visible via parent

    # else-block scope
    assert isinstance(if_stmt.else_stmt, Block)
    else_scope = resolver.get_block_scope(if_stmt.else_stmt)
    assert else_scope is not None
    assert set(else_scope.symbols.keys()) == {"y"}
    assert else_scope.lookup("b") is not None  # visible via parent


def test_match_pattern_binds_locals():
    src = """
    module m;

    enum Expr {
        Int(value: int);
        Add(left: Expr*, right: Expr*);
    }

    func eval(e: Expr*) -> int {
        match (*e) {
            Int(value) => {
                return value;
            }
            Add(left, right) => {
                let sum: int = 0;
                return sum;
            }
            _ => {
                let z: int = 0;
                return z;
            }
        }
    }
    """
    mod = parse_module(src)
    resolver = LocalScopeResolver({"m": mod})
    func_envs = resolver.resolve()

    eval_env = func_envs[("m", "eval")]
    body = eval_env.func.body
    match_stmt = body.stmts[0]
    assert isinstance(match_stmt, MatchStmt)

    arm_int, arm_add, arm_wild = match_stmt.arms

    # First arm: Int(value)
    scope_int = resolver.get_match_arm_scope(arm_int)
    assert scope_int is not None
    assert "value" in scope_int.symbols
    assert scope_int.symbols["value"].kind is LocalKind.PATTERN_VAR
    # 'e' param visible from parent
    assert scope_int.lookup("e") is not None

    # Second arm: Add(left, right) with local 'sum'
    scope_add = resolver.get_match_arm_scope(arm_add)
    assert scope_add is not None
    assert {"left", "right"}.issubset(scope_add.symbols.keys())
    assert scope_add.symbols["left"].kind is LocalKind.PATTERN_VAR
    assert scope_add.symbols["right"].kind is LocalKind.PATTERN_VAR

    # The block body of this arm shares the same scope
    body_add_scope = resolver.get_block_scope(arm_add.body)
    assert body_add_scope is scope_add
    # 'sum' is declared in the body
    assert "sum" in body_add_scope.symbols
    assert body_add_scope.symbols["sum"].kind is LocalKind.LOCAL

    # Wildcard arm does not introduce pattern vars; only local 'z'
    scope_wild = resolver.get_match_arm_scope(arm_wild)
    assert scope_wild is not None
    assert "z" in resolver.get_block_scope(arm_wild.body).symbols
    # But no pattern locals
    for name, sym in scope_wild.symbols.items():
        if sym.kind is LocalKind.PATTERN_VAR:
            raise AssertionError("Wildcard arm must not introduce pattern vars")
