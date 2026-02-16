#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from l0_ast import Span, FuncDecl, LetStmt, ReturnStmt, MatchStmt, WildcardPattern, VariantPattern
from l0_lexer import Lexer
from l0_parser import (
    Parser,
)


def parse(src: str):
    tokens = Lexer.from_source(src).tokenize()
    parser = Parser(tokens)
    return parser.parse_module()


def test_basic_spans_in_function_and_statements():
    src = """module main;

func main() -> int {
    let x: int = 0;
    return x;
}
"""
    mod = parse(src)

    # Module span covers entire file (half-open, ending at EOF position)
    assert mod.span == Span(1, 1, 6, 2)

    func = next(d for d in mod.decls if isinstance(d, FuncDecl))
    assert func.span == Span(3, 1, 6, 2)

    body = func.body
    assert body.span == Span(3, 20, 6, 2)

    let_stmt = next(s for s in body.stmts if isinstance(s, LetStmt))
    ret_stmt = next(s for s in body.stmts if isinstance(s, ReturnStmt))

    # These numbers are derived from the current lexer/parser behavior
    assert let_stmt.span == Span(4, 5, 4, 19)
    assert ret_stmt.span == Span(5, 5, 5, 13)

    # Expression spans
    assert let_stmt.value.span == Span(4, 18, 4, 19)  # the literal 0
    assert ret_stmt.value.span == Span(5, 12, 5, 13)  # the variable x

    # Return type span for the function
    assert func.return_type.span == Span(3, 16, 3, 19)


def test_match_and_pattern_spans():
    src = """module demo;

enum Expr {
    Int(value: int);
}

func f(e: Expr*) -> int {
    match (*e) {
        Int(v) => {
            return v;
        }
        _ => {
            return 0;
        }
    }
}
"""
    mod = parse(src)
    func = next(d for d in mod.decls if isinstance(d, FuncDecl))
    body = func.body

    match_stmt = next(s for s in body.stmts if isinstance(s, MatchStmt))

    # Match as a whole (match keyword through closing brace)
    assert match_stmt.span == Span(8, 5, 15, 6)

    arm1, arm2 = match_stmt.arms

    # First arm: Int(v) => { ... }
    assert arm1.span == Span(9, 9, 11, 10)
    assert isinstance(arm1.pattern, VariantPattern)
    assert arm1.pattern.span == Span(9, 9, 9, 15)

    # Second arm: _ => { ... }
    assert arm2.span == Span(12, 9, 14, 10)
    assert isinstance(arm2.pattern, WildcardPattern)
    assert arm2.pattern.span == Span(12, 9, 12, 10)
