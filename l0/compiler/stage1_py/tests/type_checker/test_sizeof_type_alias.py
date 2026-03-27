#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

from l0_types import StructType


def test_sizeof_type_alias_stores_underlying_resolved_type(analyze_single):
    # sizeof(AliasName) where AliasName is a type alias should store the underlying
    # resolved type (not alias identity).
    result = analyze_single(
        "main",
        """
        module main;

        struct Point {
            x: int;
            y: int;
        }

        type AliasPoint = Point;

        func main() -> int {
            let s: int = sizeof(AliasPoint);
            return s;
        }
        """,
    )

    assert not result.has_errors(), [d.message for d in result.diagnostics]

    assert result.intrinsic_targets, "Expected sizeof intrinsic to store a target type"

    # There should be exactly one sizeof in this program.
    assert len(result.intrinsic_targets) == 1

    (_, target_ty) = next(iter(result.intrinsic_targets.items()))
    assert isinstance(target_ty, StructType)
    assert target_ty.module == "main"
    assert target_ty.name == "Point"
