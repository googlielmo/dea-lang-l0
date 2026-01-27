#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from l0_ast import FuncDecl, Module, Block, LetStmt, AssignStmt, IfStmt, ReturnStmt, IntLiteral, BoolLiteral, VarRef, \
    UnaryOp, BinaryOp, CallExpr, IndexExpr, FieldAccessExpr, ParenExpr, CastExpr
from l0_parser import (
    Parser,
)


def parse_module(src: str) -> Module:
    parser = Parser.from_source(src)
    return parser.parse_module()


def test_if_else_and_assignment():
    src = """
    module control;

    func f(x: int) -> int {
        if (x > 0) {
            let y: int = x;
            y = y + 1;
            return y;
        } else {
            return 0;
        }
    }
    """
    mod = parse_module(src)
    assert isinstance(mod, Module)
    assert mod.name == "control"

    fn = mod.decls[0]
    assert isinstance(fn, FuncDecl)
    assert fn.name == "f"
    assert len(fn.params) == 1

    stmts = fn.body.stmts
    assert len(stmts) == 1
    if_stmt = stmts[0]
    assert isinstance(if_stmt, IfStmt)

    # condition: x > 0
    cond = if_stmt.cond
    assert isinstance(cond, BinaryOp)
    assert cond.op == ">"
    assert isinstance(cond.left, VarRef)
    assert cond.left.name == "x"
    assert isinstance(cond.right, IntLiteral)
    assert cond.right.value == 0

    # then branch
    then_s = if_stmt.then_stmt
    assert isinstance(then_s, Block)
    then_stmts = then_s.stmts
    assert len(then_stmts) == 3

    assert isinstance(then_stmts[0], LetStmt)

    assign = then_stmts[1]
    assert isinstance(assign, AssignStmt)
    assert isinstance(assign.target, VarRef)
    assert assign.target.name == "y"
    assert isinstance(assign.value, BinaryOp)
    assert assign.value.op == "+"
    assert isinstance(assign.value.left, VarRef)
    assert assign.value.left.name == "y"
    assert isinstance(assign.value.right, IntLiteral)
    assert assign.value.right.value == 1

    ret_then = then_stmts[2]
    assert isinstance(ret_then, ReturnStmt)
    assert isinstance(ret_then.value, VarRef)
    assert ret_then.value.name == "y"

    # else branch
    else_s = if_stmt.else_stmt
    assert isinstance(else_s, Block)
    else_stmts = else_s.stmts
    assert len(else_stmts) == 1
    ret_else = else_stmts[0]
    assert isinstance(ret_else, ReturnStmt)
    assert isinstance(ret_else.value, IntLiteral)
    assert ret_else.value.value == 0


def test_expression_precedence_and_postfix():
    src = """
    module expr;

    func test_ops(a: int, b: int, c: int, arr: int*, i: int) -> int {
        let x: int = 1 + 2 * 3;
        let y: int = (1 + 2) * 3;
        let z: bool = a == b || b == c && true;
        let idx: int = arr[i];
        let fld: int = arr[i].len;
        let call_result: int = get(arr[i].len);
        let cast_result: int = call_result as int;
        let neg: int = -x;
        let not_flag: bool = !true;
        return cast_result;
    }
    """
    mod = parse_module(src)
    assert isinstance(mod, Module)

    fn = mod.decls[0]
    assert isinstance(fn, FuncDecl)
    assert fn.name == "test_ops"

    stmts = fn.body.stmts
    # 10 statements: 9 lets + return
    assert len(stmts) == 10

    # let x: int = 1 + 2 * 3;
    let_x = stmts[0]
    assert isinstance(let_x, LetStmt)
    x_expr = let_x.value
    assert isinstance(x_expr, BinaryOp)
    assert x_expr.op == "+"
    assert isinstance(x_expr.left, IntLiteral)
    assert x_expr.left.value == 1
    assert isinstance(x_expr.right, BinaryOp)
    assert x_expr.right.op == "*"
    assert isinstance(x_expr.right.left, IntLiteral)
    assert x_expr.right.left.value == 2
    assert isinstance(x_expr.right.right, IntLiteral)
    assert x_expr.right.right.value == 3

    # let y: int = (1 + 2) * 3;
    let_y = stmts[1]
    assert isinstance(let_y, LetStmt)
    y_expr = let_y.value
    assert isinstance(y_expr, BinaryOp)
    assert y_expr.op == "*"
    assert isinstance(y_expr.right, IntLiteral)
    assert y_expr.right.value == 3

    # left side should be a ParenExpr wrapping 1 + 2
    assert isinstance(y_expr.left, ParenExpr)
    inner = y_expr.left.inner
    assert isinstance(inner, BinaryOp)
    assert inner.op == "+"
    assert isinstance(inner.left, IntLiteral)
    assert inner.left.value == 1
    assert isinstance(inner.right, IntLiteral)
    assert inner.right.value == 2

    # let z: bool = a == b || b == c && true;
    let_z = stmts[2]
    assert isinstance(let_z, LetStmt)
    z_expr = let_z.value
    assert isinstance(z_expr, BinaryOp)
    assert z_expr.op == "||"

    left_or = z_expr.left
    right_or = z_expr.right

    # left side: a == b
    assert isinstance(left_or, BinaryOp)
    assert left_or.op == "=="
    assert isinstance(left_or.left, VarRef)
    assert left_or.left.name == "a"
    assert isinstance(left_or.right, VarRef)
    assert left_or.right.name == "b"

    # right side: b == c && true  (&& binds tighter than ||)
    assert isinstance(right_or, BinaryOp)
    assert right_or.op == "&&"
    left_and = right_or.left
    right_and = right_or.right

    assert isinstance(left_and, BinaryOp)
    assert left_and.op == "=="
    assert isinstance(left_and.left, VarRef)
    assert left_and.left.name == "b"
    assert isinstance(left_and.right, VarRef)
    assert left_and.right.name == "c"

    assert isinstance(right_and, BoolLiteral)
    assert right_and.value is True

    # let idx: int = arr[i];
    let_idx = stmts[3]
    assert isinstance(let_idx, LetStmt)
    idx_expr = let_idx.value
    assert isinstance(idx_expr, IndexExpr)
    assert isinstance(idx_expr.array, VarRef)
    assert idx_expr.array.name == "arr"
    assert isinstance(idx_expr.index, VarRef)
    assert idx_expr.index.name == "i"

    # let fld: int = arr[i].len;
    let_fld = stmts[4]
    assert isinstance(let_fld, LetStmt)
    fld_expr = let_fld.value
    assert isinstance(fld_expr, FieldAccessExpr)
    assert fld_expr.field == "len"
    inner_idx = fld_expr.obj
    assert isinstance(inner_idx, IndexExpr)
    assert isinstance(inner_idx.array, VarRef)
    assert inner_idx.array.name == "arr"
    assert isinstance(inner_idx.index, VarRef)
    assert inner_idx.index.name == "i"

    # let call_result: int = get(arr[i].len);
    let_call = stmts[5]
    assert isinstance(let_call, LetStmt)
    call_expr = let_call.value
    assert isinstance(call_expr, CallExpr)
    assert isinstance(call_expr.callee, VarRef)
    assert call_expr.callee.name == "get"
    assert len(call_expr.args) == 1
    arg0 = call_expr.args[0]
    assert isinstance(arg0, FieldAccessExpr)
    assert isinstance(arg0.obj, IndexExpr)

    # let cast_result: int = call_result as int;
    let_cast = stmts[6]
    assert isinstance(let_cast, LetStmt)
    cast_expr = let_cast.value
    assert isinstance(cast_expr, CastExpr)
    assert isinstance(cast_expr.expr, VarRef)
    assert cast_expr.expr.name == "call_result"
    assert cast_expr.target_type.name == "int"

    # let neg: int = -x;
    let_neg = stmts[7]
    assert isinstance(let_neg, LetStmt)
    neg_expr = let_neg.value
    assert isinstance(neg_expr, UnaryOp)
    assert neg_expr.op == "-"
    assert isinstance(neg_expr.operand, VarRef)
    assert neg_expr.operand.name == "x"

    # let not_flag: bool = !true;
    let_not = stmts[8]
    assert isinstance(let_not, LetStmt)
    not_expr = let_not.value
    assert isinstance(not_expr, UnaryOp)
    assert not_expr.op == "!"
    assert isinstance(not_expr.operand, BoolLiteral)
    assert not_expr.operand.value is True

    # return cast_result;
    ret = stmts[9]
    assert isinstance(ret, ReturnStmt)
    assert isinstance(ret.value, VarRef)
    assert ret.value.name == "cast_result"
