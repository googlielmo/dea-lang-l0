#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

"""
Regression tests for `new Variant()` enum initialization.

These tests verify that heap-allocated enum variants are properly initialized
with the correct tag value. A previous bug caused `new Variant()` with no
payload to zero-initialize the struct, making all variants have tag 0.
"""


# ============================================================================
# Regression tests for new Variant() initialization
# ============================================================================


def test_new_variant_empty_payload_tag_initialization(codegen_single, compile_and_run, tmp_path):
    """
    Regression test: new Variant() with empty payload must set correct tag.

    Previously, `new Green()` would generate `{ 0 }` instead of
    `{ .tag = Color_Green }`, causing all variants to have tag 0.
    """
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            // Allocate each variant on the heap
            let r: Color* = new Red();
            let g: Color* = new Green();
            let b: Color* = new Blue();

            // Match to verify each has the correct tag
            match (*r) {
                Red() => { }
                _ => { return 1; }  // Red should match Red
            }

            match (*g) {
                Green() => { }
                _ => { return 2; }  // Green should match Green
            }

            match (*b) {
                Blue() => { }
                _ => { return 3; }  // Blue should match Blue
            }

            return 0;
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Runtime failed.\nstdout: {stdout}\nstderr: {stderr}"


def test_new_variant_with_payload_tag_initialization(codegen_single, compile_and_run, tmp_path):
    """
    Test that new Variant(payload) also initializes tag correctly.
    """
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Result {
            Ok(value: int);
            Err(code: int);
        }

        func main() -> int {
            let ok: Result* = new Ok(42);
            let err: Result* = new Err(1);

            // Verify Ok variant
            match (*ok) {
                Ok(v) => {
                    if (v != 42) { return 1; }
                }
                _ => { return 2; }
            }

            // Verify Err variant
            match (*err) {
                Err(c) => {
                    if (c != 1) { return 3; }
                }
                _ => { return 4; }
            }

            return 0;
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Runtime failed.\nstdout: {stdout}\nstderr: {stderr}"


def test_new_variant_mixed_payload_types(codegen_single, compile_and_run, tmp_path):
    """
    Test new Variant() with mix of empty and payload variants.
    """
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Event {
            Start();
            Data(value: int);
            End();
        }

        func main() -> int {
            let e1: Event* = new Start();
            let e2: Event* = new Data(123);
            let e3: Event* = new End();

            // Verify Start (empty, ordinal 0)
            match (*e1) {
                Start() => { }
                _ => { return 1; }
            }

            // Verify Data (payload, ordinal 1)
            match (*e2) {
                Data(v) => {
                    if (v != 123) { return 2; }
                }
                _ => { return 3; }
            }

            // Verify End (empty, ordinal 2)
            match (*e3) {
                End() => { }
                _ => { return 4; }
            }

            return 0;
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"

    success, stdout, stderr = compile_and_run(c_code, tmp_path)
    assert success, f"Runtime failed.\nstdout: {stdout}\nstderr: {stderr}"


def test_new_variant_codegen_has_tag_field(codegen_single):
    """
    Verify that generated C code for new Variant() includes .tag initialization.
    """
    c_code, diags = codegen_single(
        "main",
        """
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main() -> int {
            let g: Color* = new Green();
            return 0;
        }
        """,
    )

    assert c_code is not None, f"Codegen failed: {[d.message for d in diags]}"

    # The generated code must include .tag = for the Green variant
    assert ".tag = " in c_code, "Generated code must initialize .tag field"
    assert "Color_Green" in c_code, "Generated code must reference the Green tag value"
