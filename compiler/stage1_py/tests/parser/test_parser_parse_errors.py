#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from textwrap import dedent

import pytest

from l0_parser import Parser
from tests.conftest import has_error_code


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

    parser = Parser.from_source(src)
    parser.parse_module()
    assert has_error_code(parser.diagnostics, "PAR-0100")


def test_parser_malformed_module_decl():
    src = "module broken\nfunc main() -> int { return 0; }"

    parser = Parser.from_source(src)
    parser.parse_module()
    assert has_error_code(parser.diagnostics, "PAR-0312")


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

    parser = Parser.from_source(src)
    parser.parse_module()

    assert has_error_code(parser.diagnostics, "PAR-0225")


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

    parser = Parser.from_source(src)
    parser.parse_module()

    assert has_error_code(parser.diagnostics, "PAR-0176")


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

    parser = Parser.from_source(src)
    parser.parse_module()

    assert has_error_code(parser.diagnostics, "PAR-0177")


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

    parser = Parser.from_source(src)
    parser.parse_module()

    assert has_error_code(parser.diagnostics, "PAR-0176")
