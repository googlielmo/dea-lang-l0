#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from conftest import has_error_code


def test_integer_literal_bounds(analyze_single):
    ok_src = """
    module main;

    func main() -> int {
        let max: int = 2147483647;
        let min: int = -2147483648;
        return max + min;
    }
    """
    result = analyze_single("main", ok_src)
    assert not result.has_errors()

    bad_src = "2147483648"
    result = analyze_single("main", bad_src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "LEX-0060")


def test_invalid_implicit_conversion_in_new_initializer(analyze_single):
    src = """
    module main;

    func main() -> int {
        let p: int* = new int("nope");
        return 0;
    }
    """
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "TYP-0286")


def test_nullable_void_rejected(analyze_single):
    src = """
    module main;

    func main() -> void? {
        return null;
    }
    """
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "SIG-0011")


def test_enum_variant_field_unknown_type(analyze_single):
    src = """
    module main;

    enum Result {
        Ok(value: int);
        Err(value: UnknownType);
    }
    """
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "SIG-0019")


def test_enum_variant_field_non_type_symbol(analyze_single):
    src = """
    module main;

    func make() -> int { return 0; }

    enum Wrap {
        Item(value: make);
    }
    """
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "SIG-0010")


def test_illegal_recursive_value_type_cycle(analyze_single):
    src = """
    module main;

    struct A {
        b: B;
    }

    struct B {
        a: A;
    }
    """
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "SIG-0040")
