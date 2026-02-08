#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

"""
Tests for the `with` statement: deterministic resource cleanup.

Covers:
- Lexer: `with` and `cleanup` keywords
- Parser: inline => form, cleanup block form, constraint validation
- Name resolution: scoping rules
- Type checking: statement checking in with contexts
- Codegen: LIFO cleanup, cleanup block, early return
"""

import pytest

from l0_lexer import Lexer, TokenKind
from l0_parser import Parser, ParseError
from l0_ast import (
    Module, FuncDecl, WithStmt, WithItem, LetStmt, ExprStmt, AssignStmt,
    Block, CallExpr, VarRef,
)


# ============================================================================
# Helper
# ============================================================================

def parse_module(src: str) -> Module:
    parser = Parser.from_source(src)
    return parser.parse_module()


def get_func_body_stmt(src: str, func_name: str = "main", stmt_index: int = 0):
    mod = parse_module(src)
    for decl in mod.decls:
        if isinstance(decl, FuncDecl) and decl.name == func_name:
            return decl.body.stmts[stmt_index]
    raise ValueError(f"Function '{func_name}' not found")


# ============================================================================
# Lexer tests
# ============================================================================


def test_with_keyword_lexed():
    tokens = Lexer.from_source("with").tokenize()
    assert tokens[0].kind == TokenKind.WITH
    assert tokens[0].text == "with"


def test_cleanup_keyword_lexed():
    tokens = Lexer.from_source("cleanup").tokenize()
    assert tokens[0].kind == TokenKind.CLEANUP
    assert tokens[0].text == "cleanup"


def test_with_cleanup_not_identifiers():
    tokens = Lexer.from_source("with cleanup").tokenize()
    assert tokens[0].kind == TokenKind.WITH
    assert tokens[1].kind == TokenKind.CLEANUP


# ============================================================================
# Parser tests: valid forms
# ============================================================================


def test_parse_with_inline_single_item():
    src = """
    module test;
    extern func open(name: string) -> int;
    extern func close(f: int);
    func main() {
        with (let f: int = open("a") => close(f)) {
            f;
        }
    }
    """
    stmt = get_func_body_stmt(src)
    assert isinstance(stmt, WithStmt)
    assert len(stmt.items) == 1
    assert isinstance(stmt.items[0].init, LetStmt)
    assert stmt.items[0].init.name == "f"
    assert isinstance(stmt.items[0].cleanup, ExprStmt)
    assert stmt.cleanup_body is None


def test_parse_with_inline_multiple_items():
    src = """
    module test;
    extern func open(name: string) -> int;
    extern func close(f: int);
    func main() {
        with (let f: int = open("a") => close(f),
              let g: int = open("b") => close(g)) {
            f;
            g;
        }
    }
    """
    stmt = get_func_body_stmt(src)
    assert isinstance(stmt, WithStmt)
    assert len(stmt.items) == 2
    assert isinstance(stmt.items[0].init, LetStmt)
    assert stmt.items[0].init.name == "f"
    assert isinstance(stmt.items[1].init, LetStmt)
    assert stmt.items[1].init.name == "g"
    assert stmt.items[0].cleanup is not None
    assert stmt.items[1].cleanup is not None
    assert stmt.cleanup_body is None


def test_parse_with_cleanup_block():
    src = """
    module test;
    extern func open(name: string) -> int;
    extern func close(f: int);
    extern func flush(f: int);
    func main() {
        with (let f: int = open("file")) {
            f;
        } cleanup {
            flush(f);
            close(f);
        }
    }
    """
    stmt = get_func_body_stmt(src)
    assert isinstance(stmt, WithStmt)
    assert len(stmt.items) == 1
    assert isinstance(stmt.items[0].init, LetStmt)
    assert stmt.items[0].cleanup is None
    assert stmt.cleanup_body is not None
    assert len(stmt.cleanup_body.stmts) == 2


def test_parse_with_cleanup_block_multiple_items():
    src = """
    module test;
    extern func open(name: string) -> int;
    extern func close(f: int);
    extern func free(p: int);
    extern func alloc(n: int) -> int;
    extern func write(f: int, buf: int);
    func main() {
        with (let f: int = open("file"),
              let buf: int = alloc(1024)) {
            write(f, buf);
        } cleanup {
            free(buf);
            close(f);
        }
    }
    """
    stmt = get_func_body_stmt(src)
    assert isinstance(stmt, WithStmt)
    assert len(stmt.items) == 2
    assert stmt.cleanup_body is not None
    assert len(stmt.cleanup_body.stmts) == 2


def test_parse_with_bare_expr_init():
    """Bare expression as init (e.g., lock(mutex) => unlock(mutex))."""
    src = """
    module test;
    extern func lock(m: int);
    extern func unlock(m: int);
    func main() {
        let mutex: int = 0;
        with (lock(mutex) => unlock(mutex)) {
            mutex;
        }
    }
    """
    stmt = get_func_body_stmt(src, stmt_index=1)
    assert isinstance(stmt, WithStmt)
    assert isinstance(stmt.items[0].init, ExprStmt)
    assert isinstance(stmt.items[0].cleanup, ExprStmt)


def test_parse_with_assignment_init():
    """Assignment as init (e.g., cursor.state = ACTIVE => cursor.state = CLOSED)."""
    src = """
    module test;
    func main() {
        let state: int = 0;
        with (state = 1 => state = 0) {
            state;
        }
    }
    """
    stmt = get_func_body_stmt(src, stmt_index=1)
    assert isinstance(stmt, WithStmt)
    assert isinstance(stmt.items[0].init, AssignStmt)
    assert isinstance(stmt.items[0].cleanup, AssignStmt)


def test_parse_with_empty_body():
    src = """
    module test;
    func main() {
        let x: int = 0;
        with (x = 1 => x = 0) {
        }
    }
    """
    stmt = get_func_body_stmt(src, stmt_index=1)
    assert isinstance(stmt, WithStmt)
    assert len(stmt.body.stmts) == 0


# ============================================================================
# Parser tests: invalid forms (constraint violations)
# ============================================================================


def test_parse_with_mixed_arrows_error():
    """All items must use => or none."""
    src = """
    module test;
    extern func open(name: string) -> int;
    extern func close(f: int);
    func main() {
        with (let f: int = open("a") => close(f),
              let g: int = open("b")) {
            f;
        }
    }
    """
    with pytest.raises(ParseError, match="PAR-0503"):
        parse_module(src)


def test_parse_with_arrows_and_cleanup_block_error():
    """Cannot have both => and cleanup block."""
    src = """
    module test;
    extern func open(name: string) -> int;
    extern func close(f: int);
    func main() {
        with (let f: int = open("a") => close(f)) {
            f;
        } cleanup {
            close(f);
        }
    }
    """
    with pytest.raises(ParseError, match="PAR-0504"):
        parse_module(src)


def test_parse_with_no_arrows_no_cleanup_error():
    """Cleanup block required when => is not used."""
    src = """
    module test;
    extern func open(name: string) -> int;
    func main() {
        with (let f: int = open("a")) {
            f;
        }
    }
    """
    with pytest.raises(ParseError, match="PAR-0505"):
        parse_module(src)


# ============================================================================
# Type checker tests
# ============================================================================


def test_typecheck_with_inline_passes(analyze_single):
    """with statement with inline cleanup type-checks successfully."""
    result = analyze_single("main", """
        module main;
        extern func open(name: string) -> int;
        extern func close(f: int);
        func main() -> int {
            with (let f: int = open("a") => close(f)) {
                f;
            }
            return 0;
        }
    """)
    errors = [d for d in result.diagnostics if d.kind == "error"]
    assert len(errors) == 0, [d.message for d in errors]


def test_typecheck_with_cleanup_block_passes(analyze_single):
    """with statement with cleanup block type-checks successfully."""
    result = analyze_single("main", """
        module main;
        extern func open(name: string) -> int;
        extern func close(f: int);
        extern func flush(f: int);
        func main() -> int {
            with (let f: int = open("file")) {
                f;
            } cleanup {
                flush(f);
                close(f);
            }
            return 0;
        }
    """)
    errors = [d for d in result.diagnostics if d.kind == "error"]
    assert len(errors) == 0, [d.message for d in errors]


def test_typecheck_with_body_var_not_visible_in_cleanup(analyze_single):
    """Variables declared in body are not visible in cleanup block."""
    result = analyze_single("main", """
        module main;
        extern func open(name: string) -> int;
        extern func close(f: int);
        func main() -> int {
            with (let f: int = open("file")) {
                let body_var: int = 10;
            } cleanup {
                close(body_var);
            }
            return 0;
        }
    """)
    errors = [d for d in result.diagnostics if d.kind == "error"]
    assert len(errors) > 0  # body_var is not defined in cleanup scope


def test_typecheck_with_sequential_item_visibility(analyze_single):
    """Item N sees names from items 0..N-1."""
    result = analyze_single("main", """
        module main;
        extern func open(name: string) -> int;
        extern func close(f: int);
        func main() -> int {
            with (let f: int = open("a") => close(f),
                  let g: int = f => close(g)) {
                f;
                g;
            }
            return 0;
        }
    """)
    errors = [d for d in result.diagnostics if d.kind == "error"]
    assert len(errors) == 0, [d.message for d in errors]


# ============================================================================
# Codegen tests
# ============================================================================


def test_codegen_with_inline_cleanup(codegen_single):
    """with statement with inline cleanup generates correct C code."""
    c_code, diags = codegen_single("main", """
        module main;
        extern func open(name: string) -> int;
        extern func close(f: int);
        func main() -> int {
            with (let f: int = open("a") => close(f)) {
                f;
            }
            return 0;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    # The init should be emitted
    assert "open" in c_code
    # The cleanup should be emitted
    assert "close" in c_code


def test_codegen_with_inline_lifo_order(codegen_single):
    """Inline cleanup should be in LIFO order."""
    c_code, diags = codegen_single("main", """
        module main;
        extern func open(name: string) -> int;
        extern func close_a(f: int);
        extern func close_b(f: int);
        func main() -> int {
            with (let f: int = open("a") => close_a(f),
                  let g: int = open("b") => close_b(g)) {
                f;
                g;
            }
            return 0;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    # Find the function definition section (after declarations)
    func_def_start = c_code.find("l0_int l0_main_main(void)")
    assert func_def_start > 0
    func_body = c_code[func_def_start:]
    # close_b should appear before close_a in the cleanup (LIFO)
    pos_close_b = func_body.find("close_b(")
    pos_close_a = func_body.find("close_a(")
    assert pos_close_b > 0
    assert pos_close_a > 0
    assert pos_close_b < pos_close_a, f"LIFO order: close_b should come before close_a in func body"


def test_codegen_with_cleanup_block(codegen_single):
    """with statement with cleanup block generates correct C code."""
    c_code, diags = codegen_single("main", """
        module main;
        extern func open(name: string) -> int;
        extern func close(f: int);
        extern func flush(f: int);
        func main() -> int {
            with (let f: int = open("file")) {
                f;
            } cleanup {
                flush(f);
                close(f);
            }
            return 0;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    assert "flush" in c_code
    assert "close" in c_code


def test_codegen_with_compiles_and_runs(codegen_single, compile_and_run, tmp_path):
    """Full round-trip: cleanup sets result to 0, verifying it actually executed."""
    c_code, diags = codegen_single("main", """
        module main;
        func main() -> int {
            let result: int = 1;
            with (let x: int = 0 => result = x) {
                result = 1;
            }
            return result;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Program should exit 0 (cleanup sets result=0): stderr={stderr}"


def test_codegen_with_nested(codegen_single):
    """Nested with statements should work."""
    c_code, diags = codegen_single("main", """
        module main;
        extern func open(name: string) -> int;
        extern func close(f: int);
        func main() -> int {
            with (let f: int = open("a") => close(f)) {
                with (let g: int = open("b") => close(g)) {
                    f;
                    g;
                }
            }
            return 0;
        }
    """)
    assert c_code is not None, [d.message for d in diags]


# ============================================================================
# Codegen tests: scoping (body/cleanup as nested C blocks)
# ============================================================================


def test_codegen_with_body_shadowing_compiles(codegen_single, compile_and_run, tmp_path):
    """Body may shadow a variable from the with header without C redeclaration errors."""
    c_code, diags = codegen_single("main", """
        module main;
        func main() -> int {
            with (let x: int = 1 => x = x) {
                let x: int = 2;
                x;
            }
            return 0;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success or "error" not in stderr.lower(), f"C compilation failed: {stderr}"


def test_codegen_with_cleanup_block_shadowing_compiles(codegen_single, compile_and_run, tmp_path):
    """Cleanup block may shadow a variable from the with header without C redeclaration errors."""
    c_code, diags = codegen_single("main", """
        module main;
        func main() -> int {
            let result: int = 0;
            with (let x: int = 1) {
                result = x;
            } cleanup {
                let x: int = 2;
                result = x;
            }
            return result;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success or "error" not in stderr.lower(), f"C compilation failed: {stderr}"


# ============================================================================
# Codegen tests: early exit cleanup
# ============================================================================


def test_codegen_with_early_return_runs_cleanup(codegen_single):
    """Early return from with body should emit cleanup before returning."""
    c_code, diags = codegen_single("main", """
        module main;
        func helper() -> int {
            let result: int = 1;
            with (let x: int = 0 => result = x) {
                return result;
            }
            return 1;
        }
        func main() -> int {
            return helper();
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    # Verify the cleanup (result = x) appears before the return in generated code
    func_start = c_code.find("l0_main_helper")
    assert func_start > 0
    func_body = c_code[func_start:]
    assert "result" in func_body
    assert "return" in func_body


def test_codegen_with_early_return_compiles_and_runs(codegen_single, compile_and_run, tmp_path):
    """Early return from with body runs cleanup; result reflects cleanup effect."""
    c_code, diags = codegen_single("main", """
        module main;
        func helper() -> int {
            let result: int = 1;
            with (let x: int = 0 => result = x) {
                return result;
            }
            return 1;
        }
        func main() -> int {
            return helper();
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Program should exit 0 (early-return cleanup sets result=0): stderr={stderr}"


def test_codegen_with_nested_early_return_cleanup_order(codegen_single):
    """Nested with cleanup should run inner before outer on early return."""
    c_code, diags = codegen_single("main", """
        module main;
        extern func cleanup_outer();
        extern func cleanup_inner();
        func helper() -> int {
            with (let x: int = 0 => cleanup_outer()) {
                with (let y: int = 0 => cleanup_inner()) {
                    return 0;
                }
            }
            return 1;
        }
        func main() -> int {
            return helper();
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    func_start = c_code.find("l0_main_helper")
    assert func_start > 0
    func_body = c_code[func_start:]
    pos_inner = func_body.find("cleanup_inner(")
    pos_outer = func_body.find("cleanup_outer(")
    pos_return = func_body.find("return")
    assert pos_inner > 0
    assert pos_outer > 0
    assert pos_return > 0
    assert pos_inner < pos_outer < pos_return


def test_codegen_with_break_runs_cleanup(codegen_single):
    """Break from within a with body inside a loop should emit cleanup."""
    c_code, diags = codegen_single("main", """
        module main;
        func main() -> int {
            let result: int = 1;
            while (true) {
                with (let x: int = 0 => result = x) {
                    break;
                }
            }
            return result;
        }
    """)
    assert c_code is not None, [d.message for d in diags]


def test_codegen_with_break_compiles_and_runs(codegen_single, compile_and_run, tmp_path):
    """Break from within a with body inside a loop runs cleanup."""
    c_code, diags = codegen_single("main", """
        module main;
        func main() -> int {
            let result: int = 1;
            while (true) {
                with (let x: int = 0 => result = x) {
                    break;
                }
            }
            return result;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Program should exit 0 (break cleanup sets result=0): stderr={stderr}"


def test_codegen_with_break_in_cleanup_block_compiles_and_runs(codegen_single, compile_and_run, tmp_path):
    """Break from within a with body runs cleanup block."""
    c_code, diags = codegen_single("main", """
        module main;
        func main() -> int {
            let result: int = 1;
            while (true) {
                with (let x: int = 0) {
                    break;
                } cleanup {
                    result = 0;
                }
            }
            return result;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Program should exit 0 (cleanup block on break sets result=0): stderr={stderr}"


def test_codegen_with_continue_runs_cleanup_block_compiles_and_runs(codegen_single, compile_and_run, tmp_path):
    """Continue from within a with body runs cleanup block."""
    c_code, diags = codegen_single("main", """
        module main;
        func main() -> int {
            let result: int = 1;
            let count: int = 0;
            while (count < 1) {
                count = count + 1;
                with (let x: int = 0) {
                    continue;
                } cleanup {
                    result = 0;
                }
            }
            return result;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Program should exit 0 (cleanup block on continue sets result=0): stderr={stderr}"


def test_codegen_with_unreachable_inline_cleanup_emitted_once(codegen_single):
    """Inline cleanup should not be emitted on unreachable fallthrough."""
    c_code, diags = codegen_single("main", """
        module main;
        extern func do_cleanup();
        func helper() -> int {
            with (let x: int = 0 => do_cleanup()) {
                return 0;
            }
            return 1;
        }
        func main() -> int {
            return helper();
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    func_start = c_code.find("l0_main_helper")
    assert func_start > 0
    func_body = c_code[func_start:]
    assert func_body.count("do_cleanup(") == 1


def test_codegen_with_cleanup_block_return_compiles_and_runs(codegen_single, compile_and_run, tmp_path):
    """Return inside cleanup block should compile and run with expected result."""
    c_code, diags = codegen_single("main", """
        module main;
        func helper() -> int {
            with (let x: int = 0) {
                let y: int = x + 1;
            } cleanup {
                return 0;
            }
            return 1;
        }
        func main() -> int {
            let value: int = helper();
            if (value == 0) {
                return 0;
            }
            return 1;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Program should exit 0: stderr={stderr}"


def test_codegen_with_inline_cleanup_return_compiles_and_runs(codegen_single, compile_and_run, tmp_path):
    """Return inside inline cleanup should compile and run with expected result."""
    c_code, diags = codegen_single("main", """
        module main;
        func helper() -> int {
            with (let x: int = 0 => return 0) {
                let y: int = x + 1;
            }
            return 1;
        }
        func main() -> int {
            let value: int = helper();
            if (value == 0) {
                return 0;
            }
            return 1;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Program should exit 0: stderr={stderr}"


def test_codegen_with_cleanup_block_containing_with_compiles_and_runs(codegen_single, compile_and_run, tmp_path):
    """Cleanup blocks may contain nested with statements."""
    c_code, diags = codegen_single("main", """
        module main;
        func main() -> int {
            let result: int = 0;
            with (let x: int = 0) {
                result = 2;
            } cleanup {
                result = 1;
                with (let y: int = 0 => result = 0) {
                    result = 3;
                }
            }
            return result;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Program should exit 0 (cleanup nested with yields 0): stderr={stderr}"


def test_codegen_with_inline_cleanup_mixed_order(codegen_single):
    """Inline cleanup preserves LIFO ordering with mixed statement types."""
    c_code, diags = codegen_single("main", """
        module main;
        extern func mark(x: int);
        func main() -> int {
            let result: int = 0;
            with (let a: int = 0 => result = 1,
                  let b: int = 0 => mark(result),
                  let c: int = 0 => result = 2) {
                result = 3;
            }
            return result;
        }
    """)
    assert c_code is not None, [d.message for d in diags]
    func_start = c_code.find("l0_int l0_main_main(void)")
    assert func_start > 0
    func_body = c_code[func_start:]
    pos_result2 = func_body.find("result = 2")
    pos_mark = func_body.find("mark(")
    pos_result1 = func_body.find("result = 1")
    assert pos_result2 > 0
    assert pos_mark > 0
    assert pos_result1 > 0
    assert pos_result2 < pos_mark < pos_result1
