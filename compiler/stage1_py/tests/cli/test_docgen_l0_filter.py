# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
"""Tests for L0 source normalization."""

from compiler.docgen.l0_docgen_l0_filter import transform_l0_for_doxygen


def test_transform_l0_for_doxygen_rewrites_struct_fields() -> None:
    source = """
struct Span {
    start_line: int;
    name_qualifier: VectorString*?;
    fields: VectorBase*; // FieldDecl*
}
"""

    transformed = transform_l0_for_doxygen(source)

    assert "int start_line;" in transformed
    assert "VectorString* name_qualifier; /* nullable */" in transformed
    assert "VectorBase* fields; // FieldDecl*" in transformed
    assert "};" in transformed
    assert "start_line: int;" not in transformed
    assert "name_qualifier: VectorString*?;" not in transformed


def test_transform_l0_for_doxygen_rewrites_enum_members() -> None:
    source = """
enum PatternKind {
    PT_WILDCARD;
    PT_VARIANT; // keeps comment
}
"""

    transformed = transform_l0_for_doxygen(source)

    assert "PT_WILDCARD," in transformed
    assert "PT_VARIANT, // keeps comment" in transformed
    assert "};" in transformed
    assert "PT_WILDCARD;" not in transformed
