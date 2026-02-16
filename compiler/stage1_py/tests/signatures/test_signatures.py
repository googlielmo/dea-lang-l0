#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

import textwrap
from pathlib import Path

from l0_driver import L0Driver
from l0_name_resolver import NameResolver
from l0_paths import SourceSearchPaths
from l0_signatures import SignatureResolver
from l0_types import (
    BuiltinType,
    StructType,
    PointerType,
    NullableType,
    FuncType,
    get_builtin_type,
)


def _write(tmp_root: Path, rel: str, content: str) -> Path:
    path = tmp_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


def test_signature_resolution_across_modules(tmp_path):
    """
    types module defines:
      - struct Number { value: int; }
      - type IntPtr = int*;
      - func make_number(v: int) -> Number

    app.main imports types.

    We check that:
      - struct Number is StructType("types", "Number")
      - IntPtr alias resolves to PointerType(BuiltinType("int"))
      - make_number has FuncType(int -> Number)
    """
    proj_root = tmp_path / "project"
    proj_root.mkdir()

    _write(
        proj_root,
        "types.l0",
        """
        module types;

        struct Number {
            value: int;
        }

        type IntPtr = int*;

        func make_number(v: int) -> Number {
            return Number(v);
        }
        """,
    )

    _write(
        proj_root,
        "app/main.l0",
        """
        module app.main;
        import types;

        func main() -> int {
            return 0;
        }
        """,
    )

    paths = SourceSearchPaths()
    paths.add_project_root(proj_root)

    driver = L0Driver(search_paths=paths)
    cu = driver.build_compilation_unit("app.main")

    # Module-level name resolution
    nr = NameResolver(cu)
    envs = nr.resolve()

    # Signature resolution
    sr = SignatureResolver(cu, envs)
    sr.resolve()

    env_types = envs["types"]

    # struct Number
    num_sym = env_types.locals["Number"]
    assert isinstance(num_sym.type, StructType)
    assert num_sym.type.module == "types"
    assert num_sym.type.name == "Number"

    # type IntPtr
    alias_sym = env_types.locals["IntPtr"]
    assert isinstance(alias_sym.type, PointerType)
    assert isinstance(alias_sym.type.inner, BuiltinType)
    assert alias_sym.type.inner.name == "int"

    # func make_number
    fn_sym = env_types.locals["make_number"]
    assert isinstance(fn_sym.type, FuncType)
    ft = fn_sym.type
    assert len(ft.params) == 1
    assert ft.params[0] == get_builtin_type("int")
    assert ft.result == StructType("types", "Number")

    # No diagnostics expected here
    assert nr.diagnostics == []
    assert sr.diagnostics == []


def test_unknown_type_produces_diagnostic(tmp_path):
    """
    Using an unknown type in a function parameter should produce a diagnostic
    and leave the function without a resolved type.
    """
    proj_root = tmp_path / "project"
    proj_root.mkdir()

    _write(
        proj_root,
        "mod.l0",
        """
        module mod;

        func bad(x: UnknownType) -> int {
            return 0;
        }
        """,
    )

    paths = SourceSearchPaths()
    paths.add_project_root(proj_root)

    driver = L0Driver(search_paths=paths)
    cu = driver.build_compilation_unit("mod")

    nr = NameResolver(cu)
    envs = nr.resolve()

    sr = SignatureResolver(cu, envs)
    sr.resolve()

    env_mod = envs["mod"]
    fn_sym = env_mod.locals["bad"]

    # No type should have been attached due to error
    assert fn_sym.type is None

    msgs = [d.message for d in sr.diagnostics]
    assert any("unknown type 'UnknownType'" in m for m in msgs)


# ---------------------------------------------------------------------------
# New aliasing tests
# ---------------------------------------------------------------------------

def test_type_alias_chains_and_structs(tmp_path):
    """
    Single module with:
      - struct Pair { a: int; b: int; }
      - type IntAlias = int;
      - type PairAlias = Pair;
      - type PtrToInt = IntAlias*;
      - type MaybePair = PairAlias?;

    We check that aliases resolve through chains and apply pointer/nullable
    suffixes correctly.
    """
    proj_root = tmp_path / "project"
    proj_root.mkdir()

    _write(
        proj_root,
        "mod.l0",
        """
        module mod;

        struct Pair {
            a: int;
            b: int;
        }

        type IntAlias = int;
        type PairAlias = Pair;
        type PtrToInt = IntAlias*;
        type MaybePair = PairAlias?;
        """,
    )

    paths = SourceSearchPaths()
    paths.add_project_root(proj_root)

    driver = L0Driver(search_paths=paths)
    cu = driver.build_compilation_unit("mod")

    nr = NameResolver(cu)
    envs = nr.resolve()

    sr = SignatureResolver(cu, envs)
    sr.resolve()

    env_mod = envs["mod"]

    # struct Pair
    pair_sym = env_mod.locals["Pair"]
    assert isinstance(pair_sym.type, StructType)
    pair_ty = pair_sym.type
    assert pair_ty.module == "mod"
    assert pair_ty.name == "Pair"

    # type IntAlias = int;
    int_alias_sym = env_mod.locals["IntAlias"]
    assert int_alias_sym.type == get_builtin_type("int")

    # type PairAlias = Pair;
    pair_alias_sym = env_mod.locals["PairAlias"]
    assert isinstance(pair_alias_sym.type, StructType)
    assert pair_alias_sym.type == pair_ty

    # type PtrToInt = IntAlias*;
    ptr_sym = env_mod.locals["PtrToInt"]
    assert isinstance(ptr_sym.type, PointerType)
    assert ptr_sym.type.inner == get_builtin_type("int")

    # type MaybePair = PairAlias?;
    maybe_sym = env_mod.locals["MaybePair"]
    assert isinstance(maybe_sym.type, NullableType)
    assert maybe_sym.type.inner == pair_ty

    # No diagnostics expected in this positive case
    assert sr.diagnostics == []


def test_cyclic_type_aliases_produce_diagnostics(tmp_path):
    """
    Detect simple cyclic aliases:

        type A = B;
        type B = A;

    Both aliases should fail to resolve and produce a diagnostic.
    """
    proj_root = tmp_path / "project"
    proj_root.mkdir()

    _write(
        proj_root,
        "mod.l0",
        """
        module mod;

        type A = B;
        type B = A;
        """,
    )

    paths = SourceSearchPaths()
    paths.add_project_root(proj_root)

    driver = L0Driver(search_paths=paths)
    cu = driver.build_compilation_unit("mod")

    nr = NameResolver(cu)
    envs = nr.resolve()

    sr = SignatureResolver(cu, envs)
    sr.resolve()

    env_mod = envs["mod"]
    a_sym = env_mod.locals["A"]
    b_sym = env_mod.locals["B"]

    # Both aliases should have failed to resolve to a concrete type
    assert a_sym.type is None
    assert b_sym.type is None

    msgs = [d.message for d in sr.diagnostics]
    assert any("cyclic type alias involving 'A'" in m for m in msgs)
    assert any("cyclic type alias involving 'B'" in m for m in msgs)
