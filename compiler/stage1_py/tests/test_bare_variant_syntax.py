#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

"""
Tests for bare variant constructor syntax.

Zero-arg enum variants can be written as `Variant` instead of `Variant()`.
"""

from __future__ import annotations

from conftest import has_error_code


def test_bare_variant_type_check(analyze_single):
    """Bare zero-arg variant passes type checking."""
    result = analyze_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            let c: Color = Red;
            return 0;
        }
        """,
    )

    assert not result.has_errors(), f"Unexpected errors: {[d.message for d in result.diagnostics]}"


def test_bare_variant_codegen(codegen_single, compile_and_run, tmp_path):
    """Bare zero-arg variant compiles and runs correctly with match."""
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            let r: Color = Red;
            let g: Color = Green;
            let b: Color = Blue;

            match (r) {
                Red() => { }
                _ => { return 1; }
            }

            match (g) {
                Green() => { }
                _ => { return 2; }
            }

            match (b) {
                Blue() => { }
                _ => { return 3; }
            }

            return 0;
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Runtime failed.\nstdout: {stdout}\nstderr: {stderr}"


def test_bare_variant_mixed_with_call_syntax(codegen_single, compile_and_run, tmp_path):
    """Bare and call syntax can be mixed in the same program."""
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            let a: Color = Red;
            let b: Color = Green();

            match (a) {
                Red() => { }
                _ => { return 1; }
            }

            match (b) {
                Green() => { }
                _ => { return 2; }
            }

            return 0;
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Runtime failed.\nstdout: {stdout}\nstderr: {stderr}"


def test_bare_variant_in_return(codegen_single):
    """Bare variant can be used in return statements."""
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func make_red() -> Color {
            return Red;
        }

        func main() -> int {
            return 0;
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"


def test_bare_variant_as_argument(codegen_single, compile_and_run, tmp_path):
    """Bare variant can be passed as a function argument."""
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func is_red(c: Color) -> bool {
            match (c) {
                Red() => { return true; }
                _ => { return false; }
            }
        }

        func main() -> int {
            if (is_red(Red)) {
                return 0;
            }
            return 1;
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Runtime failed.\nstdout: {stdout}\nstderr: {stderr}"


def test_bare_payload_variant_error(analyze_single):
    """Bare usage of a variant with payload fields produces an error."""
    result = analyze_single(
        "main",
        """
        module main;

        enum Expr {
            Int(value: int);
            Add(left: int, right: int);
        }

        func main() -> int {
            let e: Expr = Int;
            return 0;
        }
        """,
    )

    assert result.has_errors()
    assert any("requires arguments" in d.message for d in result.diagnostics)


def test_call_syntax_still_works(analyze_single):
    """Existing call syntax `Variant()` still works."""
    result = analyze_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            let c: Color = Red();
            return 0;
        }
        """,
    )

    assert not result.has_errors(), f"Unexpected errors: {[d.message for d in result.diagnostics]}"


def test_local_shadows_enum_variant_warns(analyze_single):
    """Local shadowing of enum variant produces a warning (locals still win)."""
    result = analyze_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); }

        func main() -> int {
            let Red: int = 1;
            return Red;
        }
        """,
    )

    assert has_error_code(result.diagnostics, "TYP-0022")


def test_local_shadowing_variant_codegen_uses_local(codegen_single, compile_and_run, tmp_path):
    """Local names override bare enum variant constructors in codegen."""
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); }

        func main() -> int {
            let Red: int = 7;
            let x: int = Red;
            if (x != 7) {
                return 1;
            }
            return 0;
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Runtime failed.\nstdout: {stdout}\nstderr: {stderr}"


def test_local_shadows_imported_variant_warns(analyze_single, write_l0_file):
    """Local shadowing of an imported enum variant produces a warning."""
    write_l0_file(
        "colors",
        """
        module colors;

        enum Color { Red(); Green(); }
        """,
    )

    result = analyze_single(
        "main",
        """
        module main;
        import colors;

        func main() -> int {
            let Red: int = 1;
            return Red;
        }
        """,
    )

    assert has_error_code(result.diagnostics, "TYP-0023")
