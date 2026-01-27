#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

# test_l0_parser_ast_shapes.py

from l0_ast import FuncDecl, FieldDecl, StructDecl, EnumVariant, EnumDecl, Module, Block, ReturnStmt, MatchStmt, \
    WildcardPattern, VariantPattern, IntLiteral, VarRef, BinaryOp, CallExpr
from l0_parser import (
    Parser,
)


def parse_module(src: str) -> Module:
    parser = Parser.from_source(src)
    return parser.parse_module()


def test_struct_enum_and_match():
    src = """
    module demo;

    struct Token {
        kind: TokenKind;
        text: string;
    }

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
                return eval(left) + eval(right);
            }
            _ => {
                return 0;
            }
        }
    }
    """
    mod = parse_module(src)
    assert mod.name == "demo"
    assert len(mod.decls) == 3

    token_struct = mod.decls[0]
    expr_enum = mod.decls[1]
    eval_func = mod.decls[2]

    # struct Token
    assert isinstance(token_struct, StructDecl)
    assert token_struct.name == "Token"
    assert [f.name for f in token_struct.fields] == ["kind", "text"]
    assert isinstance(token_struct.fields[0], FieldDecl)
    assert token_struct.fields[0].type.name == "TokenKind"
    assert token_struct.fields[1].type.name == "string"

    # enum Expr
    assert isinstance(expr_enum, EnumDecl)
    assert expr_enum.name == "Expr"
    assert [v.name for v in expr_enum.variants] == ["Int", "Add"]

    int_var = expr_enum.variants[0]
    assert isinstance(int_var, EnumVariant)
    assert [f.name for f in int_var.fields] == ["value"]
    assert int_var.fields[0].type.name == "int"

    add_var = expr_enum.variants[1]
    assert [f.name for f in add_var.fields] == ["left", "right"]
    assert add_var.fields[0].type.name == "Expr"
    assert add_var.fields[0].type.pointer_depth == 1

    # func eval
    assert isinstance(eval_func, FuncDecl)
    assert eval_func.name == "eval"
    assert len(eval_func.params) == 1
    assert eval_func.params[0].name == "e"
    assert eval_func.params[0].type.name == "Expr"
    assert eval_func.params[0].type.pointer_depth == 1
    assert eval_func.return_type.name == "int"

    body_stmts = eval_func.body.stmts
    assert len(body_stmts) == 1
    match_stmt = body_stmts[0]
    assert isinstance(match_stmt, MatchStmt)
    assert len(match_stmt.arms) == 3

    arm_int, arm_add, arm_wild = match_stmt.arms

    # Int(value) arm
    assert isinstance(arm_int.pattern, VariantPattern)
    assert arm_int.pattern.name == "Int"
    assert arm_int.pattern.vars == ["value"]
    assert isinstance(arm_int.body, Block)
    assert isinstance(arm_int.body.stmts[0], ReturnStmt)

    # Add(left, right) arm
    assert isinstance(arm_add.pattern, VariantPattern)
    assert arm_add.pattern.name == "Add"
    assert arm_add.pattern.vars == ["left", "right"]
    ret_add = arm_add.body.stmts[0]
    assert isinstance(ret_add, ReturnStmt)
    sum_expr = ret_add.value
    assert isinstance(sum_expr, BinaryOp)
    assert sum_expr.op == "+"
    assert isinstance(sum_expr.left, CallExpr)
    assert isinstance(sum_expr.left.callee, VarRef)
    assert sum_expr.left.callee.name == "eval"

    # wildcard arm
    assert isinstance(arm_wild.pattern, WildcardPattern)
    ret_wild = arm_wild.body.stmts[0]
    assert isinstance(ret_wild, ReturnStmt)
    assert isinstance(ret_wild.value, IntLiteral)
    assert ret_wild.value.value == 0
