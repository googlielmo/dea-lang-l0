#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from __future__ import annotations

from conftest import has_error_code


# ============================================================================
# Type checking tests
# ============================================================================


def test_ord_simple_enum(analyze_single):
    """ord(enum_value) should type-check and return int."""
    result = analyze_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            let c: Color = Red();
            return ord(c);
        }
        """,
    )

    assert not result.has_errors(), [d.message for d in result.diagnostics]


def test_ord_enum_with_payload(analyze_single):
    """ord(enum_value) should work with payload enums."""
    result = analyze_single(
        "main",
        """
        module main;

        enum Expr {
            Int(value: int);
            Add(left: Expr*, right: Expr*);
        }

        func main() -> int {
            let e: Expr = Int(42);
            return ord(e);
        }
        """,
    )

    assert not result.has_errors(), [d.message for d in result.diagnostics]


def test_ord_inline_constructor(analyze_single):
    """ord can be called directly on enum constructor."""
    result = analyze_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            return ord(Blue());
        }
        """,
    )

    assert not result.has_errors(), [d.message for d in result.diagnostics]


def test_ord_dereferenced_pointer(analyze_single):
    """ord(*ptr) should work - dereferencing gives the enum value."""
    result = analyze_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            let cp: Color* = new Green();
            return ord(*cp);
        }
        """,
    )

    assert not result.has_errors(), [d.message for d in result.diagnostics]


def test_ord_wrong_arg_count(analyze_single):
    """ord with wrong number of arguments should produce TYP-0242."""
    result = analyze_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            let c: Color = Red();
            return ord(c, c);
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0242")


def test_ord_no_args(analyze_single):
    """ord with no arguments should produce TYP-0242."""
    result = analyze_single(
        "main",
        """
        module main;

        func main() -> int {
            return ord();
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0242")


def test_ord_non_enum_int(analyze_single):
    """ord(int) should produce TYP-0243."""
    result = analyze_single(
        "main",
        """
        module main;

        func main() -> int {
            let x: int = 42;
            return ord(x);
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0243")


def test_ord_non_enum_struct(analyze_single):
    """ord(struct) should produce TYP-0243."""
    result = analyze_single(
        "main",
        """
        module main;

        struct Point { x: int; y: int; }

        func main() -> int {
            let p: Point = Point(1, 2);
            return ord(p);
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0243")


def test_ord_non_enum_struct_pointer(analyze_single):
    """ord(struct_ptr) should produce TYP-0243 - must be enum value, not pointer."""
    result = analyze_single(
        "main",
        """
        module main;

        struct Point { x: int; y: int; }

        func main() -> int {
            let p: Point* = new Point(1, 2);
            return ord(p);
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0243")


def test_ord_non_enum_enum_pointer(analyze_single):
    """ord(enum_ptr) should produce TYP-0243 - must be enum value, not pointer."""
    result = analyze_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            let cp: Color* = new Red();
            return ord(cp);
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0243")


def test_ord_non_enum_optional(analyze_single):
    """ord(enum_optional) should produce TYP-0243 - must be plain enum, not optional."""
    result = analyze_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            let c: Color? = Red();
            return ord(c);
        }
        """,
    )

    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0243")


# ============================================================================
# Code generation tests
# ============================================================================


def test_ord_codegen_generates_tag_access(codegen_single):
    """ord(enum_value) should generate C code that accesses the .tag field."""
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            let c: Color = Red();
            return ord(c);
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"
    # Should generate access to .tag field with cast to l0_int
    assert ".tag" in c_code
    assert "l0_int" in c_code


def test_ord_codegen_inline_constructor(codegen_single):
    """ord(Constructor()) should generate correct C code."""
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            return ord(Blue());
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"
    assert ".tag" in c_code


# ============================================================================
# End-to-end runtime tests
# ============================================================================


def test_ord_runtime_values(codegen_single, compile_and_run, tmp_path):
    """Test that ord returns correct ordinal values at runtime."""
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            // Red() should be 0, Green() should be 1, Blue() should be 2
            let r: int = ord(Red());
            let g: int = ord(Green());
            let b: int = ord(Blue());

            // Test: 0 + 1 + 2 = 3
            if (r + g + b != 3) {
                return 1;
            }

            // Test individual values
            if (r != 0) { return 2; }
            if (g != 1) { return 3; }
            if (b != 2) { return 4; }

            return 0;
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Runtime failed.\nstdout: {stdout}\nstderr: {stderr}"


def test_ord_runtime_payload_enum(codegen_single, compile_and_run, tmp_path):
    """Test that ord works correctly with payload enums."""
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Result {
            Ok(value: int);
            Err(code: int);
            Unknown();
        }

        func main() -> int {
            let e1: Result = Ok(42);
            let e2: Result = Err(1);
            let e3: Result = Unknown();

            // Ok=0, Err=1, Unknown=2
            if (ord(e1) != 0) { return 1; }
            if (ord(e2) != 1) { return 2; }
            if (ord(e3) != 2) { return 3; }

            return 0;
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Runtime failed.\nstdout: {stdout}\nstderr: {stderr}"


def test_ord_runtime_dereferenced_pointer(codegen_single, compile_and_run, tmp_path):
    """Test that ord(*ptr) works correctly at runtime with new Variant()."""
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            let cp: Color* = new Green();

            // *cp is Green, which has ordinal 1
            if (ord(*cp) != 1) { return 1; }

            return 0;
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Runtime failed.\nstdout: {stdout}\nstderr: {stderr}"

