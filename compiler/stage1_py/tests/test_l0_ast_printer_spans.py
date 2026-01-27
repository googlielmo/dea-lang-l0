#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from l0_ast_printer import format_module
from l0_lexer import Lexer
from l0_parser import Parser


def parse(src: str):
    tokens = Lexer.from_source(src).tokenize()
    parser = Parser(tokens)
    return parser.parse_module()


def test_ast_printer_includes_spans_in_header_lines():
    src = """module main;

func main() -> int {
    let x: int = 0;
    return x;
}
"""
    mod = parse(src)
    printed = format_module(mod)

    # Check that the module header has a span annotation
    assert "Module(name='main') @1:1-6:2" in printed

    # Function header
    assert "FuncDecl(name='main', is_extern=False) @3:1-6:2" in printed

    # Let statement line
    assert "LetStmt(name='x') @4:5-4:19" in printed

    # Ensure that a child type span is printed on its own line
    assert "TypeRef(name='int', pointer_depth=0, is_nullable=False) @4:12-4:15" in printed
