#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from dataclasses import dataclass

import pytest

from conftest import has_error_code


@dataclass(frozen=True)
class SemanticCase:
    name: str
    doc_ref: str
    src: str
    error_code: str | None = None


VALID_CASES = [
    SemanticCase(
        name="local let inference from literal",
        doc_ref="docs/project_status.md#7-Statement-rules",
        src="""
        module main;

        func main() -> int {
            let x = 1;
            return x;
        }
        """,
    ),
    SemanticCase(
        name="top-level let inference from literal",
        doc_ref="docs/project_status.md#7-Statement-rules",
        src="""
        module main;

        let value = 10;

        func main() -> int {
            return value;
        }
        """,
    ),
    SemanticCase(
        name="implicit byte to int promotion",
        doc_ref="docs/project_status.md#7-Statement-rules",
        src="""
        module main;

        func main() -> int {
            let b: byte = 'a';
            let i: int = b;
            return i;
        }
        """,
    ),
    SemanticCase(
        name="nullable promotion T -> T?",
        doc_ref="docs/design_decisions.md#Optional-or-Nullable-Types",
        src="""
        module main;

        func main() -> int {
            let n: int? = 1;
            return 0;
        }
        """,
    ),
    SemanticCase(
        name="sizeof type intrinsic",
        doc_ref="docs/design_decisions.md#4.1-sizeof-operator",
        src="""
        module main;

        func main() -> int {
            return sizeof(int);
        }
        """,
    ),
    SemanticCase(
        name="match exhaustiveness with wildcard",
        doc_ref="docs/architecture.md#frontend-pipeline",
        src="""
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main(c: Color) -> int {
            match (c) {
                Red() => { return 1; }
                _ => { return 0; }
            }
        }
        """,
    ),
    SemanticCase(
        name="try operator in nullable-return function",
        doc_ref="docs/design_decisions.md#4.3-try-operator",
        src="""
        module main;

        func f(x: int?) -> int? {
            return x?;
        }
        """,
    ),
    SemanticCase(
        name="struct field access on non-null struct",
        doc_ref="docs/project_status.md#5-indexing--field-access",
        src="""
        module main;

        struct Point { x: int; }

        func main(p: Point) -> int {
            return p.x;
        }
        """,
    ),
]

INVALID_CASES = [
    SemanticCase(
        name="top-level let requires annotation for non-literal",
        doc_ref="docs/project_status.md#7-Statement-rules",
        src="""
        module main;

        func make() -> int { return 1; }
        let value = make();
        """,
        error_code="SIG-0030",
    ),
    SemanticCase(
        name="cannot infer local let from null",
        doc_ref="docs/project_status.md#7-Statement-rules",
        src="""
        module main;

        func main() -> int {
            let x = null;
            return 0;
        }
        """,
        error_code="TYP-0052",
    ),
    SemanticCase(
        name="cannot infer local let from void",
        doc_ref="docs/project_status.md#7-Statement-rules",
        src="""
        module main;

        func noop() -> void { return; }

        func main() -> int {
            let x = noop();
            return 0;
        }
        """,
        error_code="TYP-0053",
    ),
    SemanticCase(
        name="while condition must be bool",
        doc_ref="docs/project_status.md#7-Statement-rules",
        src="""
        module main;

        func main() -> int {
            while (1) { return 0; }
        }
        """,
        error_code="TYP-0080",
    ),
    SemanticCase(
        name="for condition must be bool",
        doc_ref="docs/project_status.md#7-Statement-rules",
        src="""
        module main;

        func main() -> int {
            for (let i: int = 0; 1; i = i + 1) { return 0; }
        }
        """,
        error_code="TYP-0090",
    ),
    SemanticCase(
        name="break outside loop",
        doc_ref="docs/project_status.md#7-Statement-rules",
        src="""
        module main;

        func main() -> int {
            break;
        }
        """,
        error_code="TYP-0110",
    ),
    SemanticCase(
        name="continue outside loop",
        doc_ref="docs/project_status.md#7-Statement-rules",
        src="""
        module main;

        func main() -> int {
            continue;
        }
        """,
        error_code="TYP-0120",
    ),
    SemanticCase(
        name="match scrutinee must be enum",
        doc_ref="docs/project_status.md#10-match-typing",
        src="""
        module main;

        func main(x: int) -> int {
            match (x) {
                _ => { return 0; }
            }
        }
        """,
        error_code="TYP-0100",
    ),
    SemanticCase(
        name="match requires exhaustiveness",
        doc_ref="docs/project_status.md#10-match-typing",
        src="""
        module main;

        enum Color { Red(); Green(); Blue(); }

        func main(c: Color) -> int {
            match (c) {
                Red() => { return 1; }
                Green() => { return 2; }
            }
        }
        """,
        error_code="TYP-0104",
    ),
    SemanticCase(
        name="match pattern arity must match variant",
        doc_ref="docs/project_status.md#10-match-typing",
        src="""
        module main;

        enum Pair { Two(a: int, b: int); }

        func main(p: Pair) -> int {
            match (p) {
                Two(x) => { return x; }
            }
        }
        """,
        error_code="TYP-0101",
    ),
    SemanticCase(
        name="match pattern must reference known variant",
        doc_ref="docs/project_status.md#10-match-typing",
        src="""
        module main;

        enum Flag { On(); Off(); }

        func main(f: Flag) -> int {
            match (f) {
                Maybe() => { return 0; }
            }
        }
        """,
        error_code="TYP-0102",
    ),
    SemanticCase(
        name="nullable struct field access rejected",
        doc_ref="docs/project_status.md#5-indexing--field-access",
        src="""
        module main;

        struct Node { value: int; }

        func main() -> int {
            let n: Node? = null;
            return n.value;
        }
        """,
        error_code="TYP-0220",
    ),
    SemanticCase(
        name="dereference requires pointer type",
        doc_ref="docs/project_status.md#9-nullable-dereference-semantics",
        src="""
        module main;

        func main() -> int {
            let p: int*? = null;
            let v: int = *p;
            return v;
        }
        """,
        error_code="TYP-0162",
    ),
    SemanticCase(
        name="invalid cast rejected",
        doc_ref="docs/project_status.md#6-casts--parens",
        src="""
        module main;

        func main() -> string {
            return 1 as string;
        }
        """,
        error_code="TYP-0230",
    ),
    SemanticCase(
        name="sizeof void rejected",
        doc_ref="docs/design_decisions.md#4.1-sizeof-operator",
        src="""
        module main;

        func main() -> int {
            return sizeof(void);
        }
        """,
        error_code="TYP-0240",
    ),
    SemanticCase(
        name="sizeof arity enforced",
        doc_ref="docs/design_decisions.md#4.1-sizeof-operator",
        src="""
        module main;

        func main() -> int {
            return sizeof(1, 2);
        }
        """,
        error_code="TYP-0241",
    ),
    SemanticCase(
        name="try operator requires nullable operand",
        doc_ref="docs/design_decisions.md#4.3-try-operator",
        src="""
        module main;

        func main(x: int) -> int? {
            return x?;
        }
        """,
        error_code="TYP-0250",
    ),
    SemanticCase(
        name="try operator requires nullable return type",
        doc_ref="docs/design_decisions.md#4.3-try-operator",
        src="""
        module main;

        func main(x: int?) -> int {
            return x?;
        }
        """,
        error_code="TYP-0251",
    ),
]


@pytest.mark.parametrize("case", VALID_CASES, ids=lambda c: f"{c.name} [{c.doc_ref}]")

def test_semantics_matrix_valid(case, analyze_single):
    # Mapping derived from docs + existing tests (e.g., test_l0_expr_typechecker_*).
    result = analyze_single("main", case.src)
    assert not result.has_errors(), f"Unexpected errors for {case.name}: {[d.message for d in result.diagnostics]}"


@pytest.mark.parametrize("case", INVALID_CASES, ids=lambda c: f"{c.name} [{c.doc_ref}]")

def test_semantics_matrix_invalid(case, analyze_single):
    result = analyze_single("main", case.src)
    assert result.has_errors(), f"Expected errors for {case.name}"
    assert case.error_code is not None
    assert has_error_code(result.diagnostics, case.error_code)
