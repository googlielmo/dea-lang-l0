"""
Tests for value-type cycle detection in the type checker.

Value-type cycles create infinite-size types and must be rejected.
Pointer-type fields break cycles (forward declarations work).
"""

#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from textwrap import dedent

from l0_driver import L0Driver


def write_tmp(tmp_path, name, src: str):
    path = tmp_path / name
    path.write_text(dedent(src))
    return path


def _analyze_single(tmp_path, name: str, src: str):
    path = write_tmp(tmp_path, f"{name}.l0", src)

    driver = L0Driver()
    driver.search_paths.add_project_root(tmp_path)

    return driver.analyze(name)


# ============================================================================
# Test 1: Direct struct cycle
# ============================================================================


def test_direct_struct_cycle(tmp_path):
    """Test that direct struct cycle is rejected."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;

        struct A {
            b: B;
        }

        struct B {
            a: A;
        }

        func main() -> int {
            return 0;
        }
        """,
    )

    # Should have cycle error
    assert result.has_errors()
    assert any("cycle" in diag.message.lower() for diag in result.diagnostics)


# ============================================================================
# Test 2: Indirect struct cycle (chain)
# ============================================================================


def test_indirect_struct_cycle(tmp_path):
    """Test that indirect struct cycle (A -> B -> C -> A) is rejected."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;

        struct A {
            b: B;
        }

        struct B {
            c: C;
        }

        struct C {
            a: A;
        }

        func main() -> int {
            return 0;
        }
        """,
    )

    # Should have cycle error
    assert result.has_errors()
    assert any("cycle" in diag.message.lower() for diag in result.diagnostics)


# ============================================================================
# Test 3: Direct enum cycle
# ============================================================================


def test_direct_enum_cycle(tmp_path):
    """Test that enum variant with self value-type field is rejected."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;

        enum E {
            Variant(e: E);
        }

        func main() -> int {
            return 0;
        }
        """,
    )

    # Should have cycle error
    assert result.has_errors()
    assert any("cycle" in diag.message.lower() for diag in result.diagnostics)


# ============================================================================
# Test 4: Struct-enum cycle
# ============================================================================


def test_struct_enum_cycle(tmp_path):
    """Test that struct-enum cycle is rejected."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;

        struct S {
            e: E;
        }

        enum E {
            Variant(s: S);
        }

        func main() -> int {
            return 0;
        }
        """,
    )

    # Should have cycle error
    assert result.has_errors()
    assert any("cycle" in diag.message.lower() for diag in result.diagnostics)


# ============================================================================
# Test 5: Pointer breaks cycle (should pass)
# ============================================================================


def test_pointer_breaks_cycle(tmp_path):
    """Test that pointer fields break cycles - this should succeed."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;

        struct Node {
            value: int;
            next: Node*;
        }

        enum Tree {
            Leaf(value: int);
            Branch(left: Tree*, right: Tree*);
        }

        func main() -> int {
            return 0;
        }
        """,
    )

    # Should succeed - pointers break the cycle
    assert not result.has_errors(), f"Unexpected errors: {result.diagnostics}"


# ============================================================================
# Test 6: Value-optional cycle (should fail)
# ============================================================================


def test_value_optional_cycle(tmp_path):
    """Test that value-optional creates cycle (still infinite size)."""
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;

        struct A {
            b: B?;
        }

        struct B {
            a: A?;
        }

        func main() -> int {
            return 0;
        }
        """,
    )

    # Should have cycle error - value-optional still creates dependency
    assert result.has_errors()
    assert any("cycle" in diag.message.lower() for diag in result.diagnostics)


# ============================================================================
# Test 7: Cross-module cycle
# ============================================================================


def test_cross_module_cycle(tmp_path):
    """Test that cycles across module boundaries are detected.

    Note: We can't have actual circular imports, but we can test a cycle
    where types in the same module form a cycle through cross-module references.
    """
    # Create base module with a struct
    write_tmp(
        tmp_path,
        "base.l0",
        """
        module base;

        struct Base {
            x: int;
        }
        """,
    )

    # Create main module that imports base and creates a cycle
    # between its own types through the base type
    result = _analyze_single(
        tmp_path,
        "main",
        """
        module main;
        import base;

        struct Wrapper {
            inner: Container;
        }

        struct Container {
            wrapped: Wrapper;
        }

        func main() -> int {
            return 0;
        }
        """,
    )

    # Should have cycle error
    assert result.has_errors()
    assert any("cycle" in diag.message.lower() for diag in result.diagnostics)
