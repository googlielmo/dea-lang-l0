#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from conftest import has_error_code


def _first_error(result):
    return next(d for d in result.diagnostics if d.kind == "error")


def test_lexer_invalid_token_reports_span(analyze_single):
    result = analyze_single("main", "@")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "LEX-0040")

    diag = _first_error(result)
    assert (diag.line, diag.column) == (1, 1)


def test_lexer_numeric_overflow_reports_span(analyze_single):
    result = analyze_single("main", "2147483648")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "LEX-0060")

    diag = _first_error(result)
    assert (diag.line, diag.column) == (1, 1)


def test_lexer_unterminated_string_reports_span(analyze_single):
    src = 'let msg = "unterminated\nnext line'
    result = analyze_single("main", src)
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "LEX-0010")

    diag = _first_error(result)
    assert (diag.line, diag.column) == (1, 24)


def test_lexer_unterminated_comment_reports_span(analyze_single):
    result = analyze_single("main", "/* comment")
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "LEX-0070")

    diag = _first_error(result)
    assert (diag.line, diag.column) == (1, 11)


def test_lexer_invalid_escape_sequences(analyze_single):
    result = analyze_single("main", '"\\xGG"')
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "LEX-0050")

    result = analyze_single("main", '"\\q"')
    assert result.has_errors()
    assert has_error_code(result.diagnostics, "LEX-0059")
