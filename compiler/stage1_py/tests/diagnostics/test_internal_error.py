#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from l0_ast import Span
from l0_internal_error import ICELocation, InternalCompilerError


def test_format_without_location():
    ice = InternalCompilerError("boom")

    assert ice.format() == "internal compiler error: [ICE-9999] boom"


def test_format_with_filename_only():
    ice = InternalCompilerError("boom", ICELocation(filename="foo.l0", span=None))

    assert ice.format() == "foo.l0: internal compiler error: [ICE-9999] boom"


def test_format_with_span_and_filename():
    span = Span(start_line=3, start_column=15, end_line=3, end_column=20)
    ice = InternalCompilerError("boom", ICELocation(filename="foo.l0", span=span))

    assert ice.format() == "foo.l0:3:15: internal compiler error: [ICE-9999] boom"

def test_format_with_ice_code_span_and_filename():
    span = Span(start_line=3, start_column=15, end_line=3, end_column=20)
    ice = InternalCompilerError("[ICE-9777] boom", ICELocation(filename="foo.l0", span=span))

    assert ice.format() == "foo.l0:3:15: internal compiler error: [ICE-9777] boom"
