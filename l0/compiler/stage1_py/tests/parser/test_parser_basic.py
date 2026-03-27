#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from l0_ast import FuncDecl, Module, Block, LetStmt, WhileStmt, ReturnStmt, IntLiteral, VarRef, BinaryOp
from l0_parser import (
    Parser,
)


def parse_module(src: str) -> Module:
    parser = Parser.from_source(src)
    mod = parser.parse_module()
    assert isinstance(mod, Module)
    return mod


def test_minimal_main():
    src = """
    module main;

    func main() -> int {
        let x: int = 0;
        while (x < 10) {
            x = x + 1;
        }
        return x;
    }
    """
    mod = parse_module(src)

    # module name
    assert mod.name == "main"
    assert len(mod.imports) == 0
    assert len(mod.decls) == 1

    main_decl = mod.decls[0]
    assert isinstance(main_decl, FuncDecl)
    assert main_decl.name == "main"
    assert main_decl.params == []
    assert main_decl.return_type.name == "int"
    assert isinstance(main_decl.body, Block)

    # body statements: let, while, return
    stmts = main_decl.body.stmts
    assert len(stmts) == 3

    let = stmts[0]
    assert isinstance(let, LetStmt)
    assert let.name == "x"
    assert let.type.name == "int"
    assert isinstance(let.value, IntLiteral)
    assert let.value.value == 0

    loop = stmts[1]
    assert isinstance(loop, WhileStmt)
    # condition: (x < 10)
    cond = loop.cond
    assert isinstance(cond, BinaryOp)
    assert cond.op == "<"
    assert isinstance(cond.left, VarRef)
    assert cond.left.name == "x"
    assert isinstance(cond.right, IntLiteral)
    assert cond.right.value == 10

    ret = stmts[2]
    assert isinstance(ret, ReturnStmt)
    assert isinstance(ret.value, VarRef)
    assert ret.value.name == "x"
