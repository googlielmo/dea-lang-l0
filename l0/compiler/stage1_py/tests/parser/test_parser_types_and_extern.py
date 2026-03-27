#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from l0_ast import FuncDecl, Module
from l0_parser import Parser


def parse_module(src: str) -> Module:
    parser = Parser.from_source(src)
    return parser.parse_module()


def test_extern_and_types():
    src = """
    module stdio;

    extern func rt_print_int(x: int) -> void;
    extern func rt_alloc(bytes: int) -> void*?;
    """
    mod = parse_module(src)
    assert mod.name == "stdio"
    assert len(mod.decls) == 2

    f1 = mod.decls[0]
    f2 = mod.decls[1]

    assert isinstance(f1, FuncDecl)
    assert f1.is_extern
    assert f1.name == "rt_print_int"
    assert f1.return_type.name == "void"
    assert f1.return_type.pointer_depth == 0
    assert not f1.return_type.is_nullable

    assert isinstance(f2, FuncDecl)
    assert f2.is_extern
    assert f2.name == "rt_alloc"
    assert f2.return_type.name == "void"
    assert f2.return_type.pointer_depth == 1
    assert f2.return_type.is_nullable
