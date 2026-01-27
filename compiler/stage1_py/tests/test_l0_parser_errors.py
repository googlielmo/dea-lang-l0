#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from textwrap import dedent

import pytest

from l0_parser import ParseError, Parser


def test_parser_missing_semicolon_reports_error():
    src = dedent(
        """
        module main;

        func main() -> int {
            let x: int = 0
            return x;
        }
        """
    )

    with pytest.raises(ParseError) as excinfo:
        Parser.from_source(src).parse_module()

    assert "expected ';'" in excinfo.value.message
    assert excinfo.value.token is not None


def test_parser_malformed_module_decl():
    src = "module broken\nfunc main() -> int { return 0; }"

    with pytest.raises(ParseError) as excinfo:
        Parser.from_source(src).parse_module()

    assert "expected ';' after module name" in excinfo.value.message
    assert excinfo.value.token is not None


def test_parser_unexpected_token():
    src = dedent(
        """
        module main;

        func main() -> int {
            if (true) {
                return 0;
            ]
        }
        """
    )

    with pytest.raises(ParseError) as excinfo:
        Parser.from_source(src).parse_module()

    assert "unexpected token" in excinfo.value.message
    assert excinfo.value.token is not None


# ============================================================================
# Match statement validation tests
# ============================================================================


def test_parser_match_duplicate_variant_pattern():
    """Test that duplicate variant patterns in match are rejected."""
    src = dedent(
        """
        module main;

        enum Option { None; Some(v: int); }

        func test(x: Option) -> int {
            match (x) {
                Some(a) => { return a; }
                Some(b) => { return b; }
            }
        }
        """
    )

    with pytest.raises(ParseError) as excinfo:
        Parser.from_source(src).parse_module()

    assert "duplicate variant patterns" in excinfo.value.message


def test_parser_match_empty_arms():
    """Test that match with no arms is rejected."""
    src = dedent(
        """
        module main;

        enum Option { None; Some(v: int); }

        func test(x: Option) -> int {
            match (x) {
            }
        }
        """
    )

    with pytest.raises(ParseError) as excinfo:
        Parser.from_source(src).parse_module()

    assert "at least one arm" in excinfo.value.message


def test_parser_match_multiple_wildcards():
    """Test that multiple wildcard patterns in match are rejected."""
    src = dedent(
        """
        module main;

        enum Option { None; Some(v: int); }

        func test(x: Option) -> int {
            match (x) {
                _ => { return 0; }
                _ => { return 1; }
            }
        }
        """
    )

    with pytest.raises(ParseError) as excinfo:
        Parser.from_source(src).parse_module()

    assert "duplicate variant patterns" in excinfo.value.message
