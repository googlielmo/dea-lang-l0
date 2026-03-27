#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from l0_ast import Import, FuncDecl, FieldDecl, StructDecl, EnumVariant, EnumDecl, TypeAliasDecl, Module, ReturnStmt, \
    StringLiteral, BoolLiteral
from l0_parser import (
    Parser,
)


def parse_module(src: str) -> Module:
    parser = Parser.from_source(src)
    return parser.parse_module()


def test_imports_and_type_decls():
    src = """
    module demo;

    import ast;
    import std.collections;

    type RawPtr = void*;

    struct Node {
        next: Node*?;
        value: int;
    }

    enum MaybeInt {
        None;
        Some(value: int);
    }

    func use(p: RawPtr, n: Node*?) -> bool {
        return true;
    }

    func hello() -> string {
        return "hello";
    }
    """
    mod = parse_module(src)

    assert isinstance(mod, Module)
    assert mod.name == "demo"

    # imports
    assert len(mod.imports) == 2
    assert isinstance(mod.imports[0], Import)
    assert mod.imports[0].name == "ast"
    assert isinstance(mod.imports[1], Import)
    assert mod.imports[1].name == "std.collections"

    # decl order: type alias, struct, enum, func, func
    alias, node_struct, maybe_enum, use_func, hello_func = mod.decls

    # type RawPtr = void*;
    assert isinstance(alias, TypeAliasDecl)
    assert alias.name == "RawPtr"
    assert alias.target.name == "void"
    assert alias.target.pointer_depth == 1
    assert not alias.target.is_nullable

    # struct Node { next: Node*?; value: int; }
    assert isinstance(node_struct, StructDecl)
    assert node_struct.name == "Node"
    assert [f.name for f in node_struct.fields] == ["next", "value"]

    next_field, value_field = node_struct.fields
    assert isinstance(next_field, FieldDecl)
    assert next_field.type.name == "Node"
    assert next_field.type.pointer_depth == 1
    assert next_field.type.is_nullable

    assert isinstance(value_field, FieldDecl)
    assert value_field.type.name == "int"
    assert value_field.type.pointer_depth == 0
    assert not value_field.type.is_nullable

    # enum MaybeInt { None; Some(value: int); }
    assert isinstance(maybe_enum, EnumDecl)
    assert maybe_enum.name == "MaybeInt"
    assert [v.name for v in maybe_enum.variants] == ["None", "Some"]

    none_var, some_var = maybe_enum.variants
    assert isinstance(none_var, EnumVariant)
    assert none_var.fields == []

    assert isinstance(some_var, EnumVariant)
    assert [f.name for f in some_var.fields] == ["value"]
    assert some_var.fields[0].type.name == "int"

    # func use(p: RawPtr, n: Node*?) -> bool { return true; }
    assert isinstance(use_func, FuncDecl)
    assert use_func.name == "use"
    assert len(use_func.params) == 2
    p_param, n_param = use_func.params

    assert p_param.name == "p"
    assert p_param.type.name == "RawPtr"
    assert p_param.type.pointer_depth == 0

    assert n_param.name == "n"
    assert n_param.type.name == "Node"
    assert n_param.type.pointer_depth == 1
    assert n_param.type.is_nullable

    assert use_func.return_type.name == "bool"

    use_body = use_func.body.stmts
    assert len(use_body) == 1
    ret = use_body[0]
    assert isinstance(ret, ReturnStmt)
    assert isinstance(ret.value, BoolLiteral)
    assert ret.value.value is True

    # func hello() -> string { return "hello"; }
    assert isinstance(hello_func, FuncDecl)
    assert hello_func.name == "hello"
    assert hello_func.return_type.name == "string"

    hello_body = hello_func.body.stmts
    assert len(hello_body) == 1
    ret_hello = hello_body[0]
    assert isinstance(ret_hello, ReturnStmt)
    assert isinstance(ret_hello.value, StringLiteral)
    assert ret_hello.value.value == "hello"


def test_dotted_module_and_imports():
    src = """
    module myapp.data;

    import std.collections;
    import myapp.data.internal;
    """
    mod = parse_module(src)
    assert mod.name == "myapp.data"
    assert [imp.name for imp in mod.imports] == [
        "std.collections",
        "myapp.data.internal",
    ]
