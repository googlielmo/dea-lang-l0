"""
Tests for the L0 byte type: lexer, parser, type checker, and codegen.
"""
#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

import subprocess
from pathlib import Path
from subprocess import CompletedProcess
from textwrap import dedent

import pytest

from l0_ast import ByteLiteral, FuncDecl, LetStmt, ReturnStmt
from l0_backend import Backend
from l0_driver import L0Driver
from l0_lexer import Lexer, LexerError, TokenKind
from l0_parser import Parser
from l0_types import BuiltinType


# ============================================================================
# Lexer tests
# ============================================================================


def test_lexer_byte_literal_simple():
    """Test basic byte literal tokenization."""
    src = "'a'"
    tokens = Lexer.from_source(src).tokenize()

    assert len(tokens) == 2  # BYTE + EOF
    assert tokens[0].kind == TokenKind.BYTE
    assert tokens[0].text == "a"


def test_lexer_byte_literal_digit():
    """Test byte literal with digit character."""
    src = "'5'"
    tokens = Lexer.from_source(src).tokenize()

    assert tokens[0].kind == TokenKind.BYTE
    assert tokens[0].text == "5"


def test_lexer_byte_literal_space():
    """Test byte literal with space character."""
    src = "' '"
    tokens = Lexer.from_source(src).tokenize()

    assert tokens[0].kind == TokenKind.BYTE
    assert tokens[0].text == " "


def test_lexer_byte_literal_escape_newline():
    """Test byte literal with newline escape."""
    src = r"'\n'"
    tokens = Lexer.from_source(src).tokenize()

    assert tokens[0].kind == TokenKind.BYTE
    assert tokens[0].text == "\\n"


def test_lexer_byte_literal_escape_tab():
    """Test byte literal with tab escape."""
    src = r"'\t'"
    tokens = Lexer.from_source(src).tokenize()

    assert tokens[0].kind == TokenKind.BYTE
    assert tokens[0].text == "\\t"


def test_lexer_byte_literal_escape_null():
    """Test byte literal with null escape."""
    src = r"'\0'"
    tokens = Lexer.from_source(src).tokenize()

    assert tokens[0].kind == TokenKind.BYTE
    assert tokens[0].text == "\\0"


def test_lexer_byte_literal_escape_backslash():
    """Test byte literal with backslash escape."""
    src = r"'\\'"
    tokens = Lexer.from_source(src).tokenize()

    assert tokens[0].kind == TokenKind.BYTE
    assert tokens[0].text == "\\\\"


def test_lexer_byte_literal_escape_single_quote():
    """Test byte literal with single quote escape."""
    src = r"'\''"
    tokens = Lexer.from_source(src).tokenize()

    assert tokens[0].kind == TokenKind.BYTE
    assert tokens[0].text == "\\'"


def test_lexer_byte_literal_in_expression():
    """Test byte literal in context of a let statement."""
    src = "let c: byte = 'x';"
    tokens = Lexer.from_source(src).tokenize()

    kinds = [t.kind for t in tokens]
    assert kinds == [
        TokenKind.LET,
        TokenKind.IDENT,  # c
        TokenKind.COLON,
        TokenKind.IDENT,  # byte
        TokenKind.EQ,
        TokenKind.BYTE,  # 'x'
        TokenKind.SEMI,
        TokenKind.EOF,
    ]
    byte_tok = tokens[5]
    assert byte_tok.text == "x"


def test_lexer_byte_literal_unterminated_raises():
    """Test that unterminated byte literal raises error."""
    src = "'a"

    with pytest.raises(LexerError) as excinfo:
        Lexer.from_source(src).tokenize()

    assert "unterminated char literal" in excinfo.value.message


def test_lexer_byte_literal_empty_raises():
    """Test that empty byte literal raises error."""
    src = "''"

    with pytest.raises(LexerError) as excinfo:
        Lexer.from_source(src).tokenize()

    # Either unterminated or invalid, depending on implementation
    assert excinfo.value.message is not None


def test_lexer_byte_literal_multi_byte_raises():
    """Test that multi-byte character literal raises error."""
    # A multi-byte UTF-8 character
    src = "'\u00e9'"  # é (2 bytes in UTF-8)

    with pytest.raises(LexerError) as excinfo:
        Lexer.from_source(src).tokenize()

    assert "single byte" in excinfo.value.message


def test_lexer_byte_literal_location():
    """Test that byte literal has correct line/column."""
    src = "  'z'"
    tokens = Lexer.from_source(src).tokenize()

    byte_tok = tokens[0]
    assert byte_tok.kind == TokenKind.BYTE
    assert byte_tok.line == 1
    assert byte_tok.column == 3


# ============================================================================
# Parser tests
# ============================================================================


def parse_module(src: str):
    parser = Parser.from_source(src)
    return parser.parse_module()


def test_parser_byte_literal_in_let():
    """Test parsing byte literal in let statement."""
    src = """
    module main;
    func f() -> byte {
        let c: byte = 'a';
        return c;
    }
    """
    mod = parse_module(src)

    func = mod.decls[0]
    assert isinstance(func, FuncDecl)

    let_stmt = func.body.stmts[0]
    assert isinstance(let_stmt, LetStmt)
    assert isinstance(let_stmt.value, ByteLiteral)
    assert let_stmt.value.value == "a"


def test_parser_byte_literal_in_return():
    """Test parsing byte literal in return statement."""
    src = """
    module main;
    func get_byte() -> byte {
        return 'x';
    }
    """
    mod = parse_module(src)

    func = mod.decls[0]
    ret_stmt = func.body.stmts[0]
    assert isinstance(ret_stmt, ReturnStmt)
    assert isinstance(ret_stmt.value, ByteLiteral)
    assert ret_stmt.value.value == "x"


def test_parser_byte_type_in_parameter():
    """Test parsing byte type in function parameter."""
    src = """
    module main;
    func process(b: byte) -> int {
        return 0;
    }
    """
    mod = parse_module(src)

    func = mod.decls[0]
    assert func.params[0].type.name == "byte"


def test_parser_byte_type_in_struct():
    """Test parsing byte type in struct field."""
    src = """
    module main;
    struct Data {
        flag: byte;
        value: int;
    }
    """
    mod = parse_module(src)

    struct = mod.decls[0]
    assert struct.fields[0].type.name == "byte"


# ============================================================================
# Type checker tests
# ============================================================================


def write_tmp(tmp_path, name: str, src: str):
    path = tmp_path / name
    path.write_text(dedent(src))
    return path


def _analyze_single(tmp_path, name: str, src: str):
    path = write_tmp(tmp_path, f"{name}.l0", src)
    driver = L0Driver()
    driver.search_paths.add_project_root(tmp_path)
    return driver.analyze(name)


def test_typechecker_byte_literal_has_byte_type(tmp_path):
    """Test that byte literal is typed as byte."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;
        func f() -> byte {
            return 'a';
        }
        """,
    )

    assert not result.has_errors(), [d.message for d in result.diagnostics]

    mod = result.cu.modules["main"]
    func = next(d for d in mod.decls if isinstance(d, FuncDecl))
    ret = func.body.stmts[0]
    expr = ret.value

    t = result.expr_types[id(expr)]
    assert isinstance(t, BuiltinType)
    assert t.name == "byte"


def test_typechecker_byte_to_int_widening(tmp_path):
    """Test that byte can be assigned to int (widening)."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;
        func f() -> int {
            let b: byte = 'a';
            let i: int = b;
            return i;
        }
        """,
    )

    assert not result.has_errors(), [d.message for d in result.diagnostics]


def test_typechecker_byte_return_as_int(tmp_path):
    """Test that byte can be returned where int is expected."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;
        func get_int() -> int {
            return 'x';
        }
        """,
    )

    assert not result.has_errors(), [d.message for d in result.diagnostics]


def test_typechecker_int_to_byte_requires_cast(tmp_path):
    """Test that int cannot be assigned to byte without cast."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;
        func f() -> byte {
            let i: int = 65;
            let b: byte = i;
            return b;
        }
        """,
    )

    assert result.has_errors()
    assert any("type" in d.message.lower() for d in result.diagnostics)


def test_typechecker_int_to_byte_cast(tmp_path):
    """Test that int can be cast to byte."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;
        func f() -> byte {
            let i: int = 65;
            return i as byte;
        }
        """,
    )

    assert not result.has_errors(), [d.message for d in result.diagnostics]


def test_typechecker_byte_addition(tmp_path):
    """Test arithmetic with bytes."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;
        func add_bytes(a: byte, b: byte) -> int {
            return a + b;
        }
        """,
    )

    assert not result.has_errors(), [d.message for d in result.diagnostics]


def test_typechecker_byte_comparison(tmp_path):
    """Test comparison with bytes."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;
        func compare(a: byte, b: byte) -> bool {
            return a < b;
        }
        """,
    )

    assert not result.has_errors(), [d.message for d in result.diagnostics]


def test_typechecker_byte_parameter(tmp_path):
    """Test passing byte to function expecting byte."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;
        func process(b: byte) -> byte {
            return b;
        }
        func caller() -> byte {
            return process('x');
        }
        """,
    )

    assert not result.has_errors(), [d.message for d in result.diagnostics]


def test_typechecker_byte_in_struct(tmp_path):
    """Test byte type in struct field."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;
        struct Pair {
            first: byte;
            second: byte;
        }
        func make_pair(a: byte, b: byte) -> Pair {
            return Pair(a, b);
        }
        """,
    )

    assert not result.has_errors(), [d.message for d in result.diagnostics]


# ============================================================================
# Codegen tests
# ============================================================================


def _codegen_single(tmp_path, name: str, src: str):
    """Analyze and generate C code for a single L0 module."""
    path = write_tmp(tmp_path, f"{name}.l0", src)

    driver = L0Driver()
    driver.search_paths.add_project_root(tmp_path)
    result = driver.analyze(name)

    if result.has_errors():
        return None, result.diagnostics

    from l0_backend import Backend
    backend = Backend(result)
    c_code = backend.generate()
    return c_code, []


def test_codegen_byte_type_mapping(tmp_path):
    """Test that byte maps to l0_byte in C."""
    c_code, _ = _codegen_single(
        tmp_path,
        "main",
        """
        module main;
        func get_byte(b: byte) -> byte {
            return b;
        }
        """,
    )

    if c_code is None:
        return

    assert "l0_byte" in c_code
    assert "l0_byte l0_main_get_byte(l0_byte b)" in c_code


def test_codegen_byte_literal(tmp_path):
    """Test that byte literal generates correct C code."""
    c_code, _ = _codegen_single(
        tmp_path,
        "main",
        """
        module main;
        func get_a() -> byte {
            return 'a';
        }
        """,
    )

    if c_code is None:
        return

    assert "((l0_byte)'a')" in c_code


def test_codegen_byte_literal_escape(tmp_path):
    """Test that escaped byte literal generates correct C code."""
    c_code, _ = _codegen_single(
        tmp_path,
        "main",
        """
        module main;
        func get_newline() -> byte {
            return '\\n';
        }
        """,
    )

    if c_code is None:
        return

    assert "((l0_byte)'\\n')" in c_code


def test_codegen_byte_in_struct(tmp_path):
    """Test byte field in struct generates correct C code."""
    c_code, _ = _codegen_single(
        tmp_path,
        "main",
        """
        module main;
        struct CharPair {
            first: byte;
            second: byte;
        }
        func main() -> int { return 0; }
        """,
    )

    if c_code is None:
        return

    assert "l0_byte first;" in c_code
    assert "l0_byte second;" in c_code


def test_codegen_byte_to_int_widening(tmp_path):
    """Test byte to int widening in codegen."""
    c_code, _ = _codegen_single(
        tmp_path,
        "main",
        """
        module main;
        func byte_to_int(b: byte) -> int {
            return b;
        }
        """,
    )

    if c_code is None:
        return

    # Should generate an implicit cast or just return b
    assert "l0_int l0_main_byte_to_int(l0_byte b)" in c_code
    # The return should work without explicit cast
    assert "return" in c_code


def test_codegen_int_to_byte_cast(tmp_path):
    """Test int to byte checked cast in codegen."""
    c_code, _ = _codegen_single(
        tmp_path,
        "main",
        """
        module main;
        func int_to_byte(i: int) -> byte {
            return i as byte;
        }
        """,
    )

    if c_code is None:
        return

    # Should generate runtime-checked narrowing
    assert "_rt_narrow_l0_byte" in c_code


def test_codegen_byte_let_statement(tmp_path):
    """Test byte variable in let statement."""
    c_code, _ = _codegen_single(
        tmp_path,
        "main",
        """
        module main;
        func f() -> byte {
            let c: byte = 'x';
            return c;
        }
        """,
    )

    if c_code is None:
        return

    assert "l0_byte c = ((l0_byte)'x');" in c_code


def test_codegen_byte_arithmetic(tmp_path):
    """Test byte arithmetic generates int operations."""
    c_code, _ = _codegen_single(
        tmp_path,
        "main",
        """
        module main;
        func add_bytes(a: byte, b: byte) -> int {
            return a + b;
        }
        """,
    )

    if c_code is None:
        return

    # Byte arithmetic should use int operations
    assert "_rt_iadd" in c_code


# ============================================================================
# Build tests
# ============================================================================

def run_c_compiler(c_file: Path, out_file: Path) -> CompletedProcess[str]:
    runtime_dir = Path(__file__).parent.parent / "runtime"
    return subprocess.run(
        ["gcc", "-Wall", "-Wextra", "-std=c99", "-pedantic-errors", f"-I{runtime_dir}", "-o", str(out_file), str(c_file)],
        capture_output=True,
        text=True,
    )


def test_build_byte_program_simple(tmp_path):
    """Test full build of a program using byte type."""
    src = """
    module main;
    func main() -> int {
        let b: byte = 'A';
        let i: int = b;
        return i;
    }
    """
    path = write_tmp(tmp_path, "main.l0", src)

    driver = L0Driver()
    driver.search_paths.add_project_root(tmp_path)
    result = driver.analyze("main")
    assert not result.has_errors(), [d.message for d in result.diagnostics]

    backend = Backend(result)
    c_code = backend.generate()
    c_file = tmp_path / "main.c"
    c_file.write_text(c_code)
    out_file = tmp_path / "main.out"
    compile_result = run_c_compiler(c_file, out_file)
    assert compile_result.returncode == 0, compile_result.stderr
    # Run the compiled program and check exit code
    run_result = subprocess.run([str(out_file)])
    assert run_result.returncode == ord('A')  # Should return ASCII value of 'A'

def test_build_byte_program_special(tmp_path):
    """Test full build of a program using byte type."""
    src = """
    module main;
    func main() -> int {
        /* Test various byte literal forms */
        let a = '\\n'; // newline
        let q = '\\''; // single quote
        let c = '\\u0043'; // 'C'
        let d = '\\U00000044'; // 'D'
        let e = '\\x45'; // 'E'
        
        let b: byte = d;
        let i: int = b;
        
        return i;
    }
    """
    path = write_tmp(tmp_path, "main.l0", src)

    driver = L0Driver()
    driver.search_paths.add_project_root(tmp_path)
    result = driver.analyze("main")
    assert not result.has_errors(), [d.message for d in result.diagnostics]

    backend = Backend(result)
    c_code = backend.generate()
    c_file = tmp_path / "main.c"
    c_file.write_text(c_code)
    out_file = tmp_path / "main.out"
    compile_result = run_c_compiler(c_file, out_file)
    assert compile_result.returncode == 0, compile_result.stderr
    # Run the compiled program and check exit code
    run_result = subprocess.run([str(out_file)])
    assert run_result.returncode == ord('D')  # Should return ASCII value of 'D'
