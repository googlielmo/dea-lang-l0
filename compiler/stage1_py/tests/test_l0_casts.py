"""
Comprehensive tests for cast expressions in L0.

Tests both type checking and code generation.
"""

#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from textwrap import dedent

import l0_backend
from l0_driver import L0Driver


def write_tmp(tmp_path, name: str, src: str):
    path = tmp_path / name
    path.write_text(dedent(src))
    return path


def _analyze_single(tmp_path, name: str, src: str):
    path = write_tmp(tmp_path, f"{name}.l0", src)

    driver = L0Driver()
    driver.search_paths.add_project_root(tmp_path)

    return driver.analyze(name)


# ============================================================================
# Cast expression type checking tests
# ============================================================================


def test_casts_basic_types(tmp_path):
    """Test basic casts between compatible types."""
    result = _analyze_single(
        tmp_path,
        "casts",
        """
        module casts;
        
        func int_to_optional(n: int) -> int? {
            return n as int?;
        }
        
        func optional_to_int(n: int?) -> int {
            if (n != null) {
                return n as int;
            } else {
                return 0;
            }
        }
        
        func pointer_to_nullable(p: int*) -> int*? {
            return p as int*?;
        }
        
        func nullable_to_pointer_or_default(p: int*?, default: int*) -> int* {
            if (p != null) {
                return p as int*;
            } else {
                return default;
            }
        }
        """,
    )

    # Try to generate C code

    assert result.has_errors() == False

    backend = l0_backend.Backend(result)
    c_code = backend.generate()

    assert c_code is not None

    assert not result.has_errors()

def test_casts_pointer_nullability(tmp_path):
    """Test casts involving pointer nullability."""
    result = _analyze_single(
        tmp_path,
        "casts",
        """
        module casts;

        func pointer_to_nullable(p: int*) -> int*? {
            return p as int*?;
        }
        
        func nullable_to_pointer(p: int*?) -> int* {
            if (p != null) {
                return p as int*;
            } else {
                return null;  // Should be a type error (cannot return null for non-nullable)
            }
        }
        """,
    )

    assert result.has_errors()
    assert len(result.diagnostics) == 1
    assert any("return value type mismatch: expected 'int*', got 'null'" in d.message for d in result.diagnostics)

def test_casts_wrong_types(tmp_path):
    """Test casts with wrong types."""
    result = _analyze_single(
        tmp_path,
        "casts",
        """
        module casts;

        func bad_string_to_int() -> int {
            return "hello" as int;   // Should be a type error (string cannot be cast to int)
        }
        
        func bad_int_to_string() -> string {
            return 42 as string;     // Should be a type error (int cannot be cast to string)
        }
        
        func bool_to_int_cast(flag: bool) -> int {
            return flag as int;      // Likely unsafe; should be rejected once cast rules are enforced
        }
        """,
    )

    assert result.has_errors()
    assert len(result.diagnostics) == 3
    assert any("cannot cast from string to int" in d.message for d in result.diagnostics)
    assert any("cannot cast from int to string" in d.message for d in result.diagnostics)
    assert any("cannot cast from bool to int" in d.message for d in result.diagnostics)

def  test_casts_wrong_enum_struct(tmp_path):
    """Test casts involving enums and structs."""
    result = _analyze_single(
        tmp_path,
        "casts",
        """  
        module casts;  
  
        enum Color {  
            Red;  
            Green;  
            Blue;  
        }   
        struct Point {  
            x: int;  
            y: int;  
        }
        func enum_to_int(c: Color) -> int {
            return c as int;
        }
        func int_to_enum(n: int) -> Color {
            return n as Color;
        }
        func struct_to_pointer(p: Point) -> Point* {
            return p as Point*;
        }
        func pointer_to_struct(p: Point*) -> Point {
            return p as Point;
        }
        """,
    )

    assert result.has_errors()
    assert len(result.diagnostics) == 4

    assert any("cannot cast from casts::Color to int" in d.message for d in result.diagnostics)
    assert any("cannot cast from int to casts::Color" in d.message for d in result.diagnostics)
    assert any("cannot cast from casts::Point to casts::Point*" in d.message for d in result.diagnostics)
    assert any("cannot cast from casts::Point* to casts::Point" in d.message for d in result.diagnostics)
