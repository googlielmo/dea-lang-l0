#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

"""
ARC trace runtime verification tests.

Each test compiles an L0 program with trace_arc=True, runs it, parses the
structured ``[l0][arc]`` lines from stderr, and asserts on refcount
transitions, action outcomes, and leak-freedom invariants.

Trace line format (from l0_runtime.h):
    [l0][arc] op=<retain|release> kind=<static|heap> ptr=<hex>
              rc_before=<int> rc_after=<int> action=<noop|retain|keep|free|...>
"""

import re
from collections import defaultdict

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ARC_LINE_RE = re.compile(r"^\[l0\]\[arc\] (.+)$")
_KV_RE = re.compile(r"(\w+)=(\S+)")


def parse_arc_lines(stderr: str) -> list[dict[str, str]]:
    """Extract ``[l0][arc]`` lines and split key=value tokens into dicts."""
    results: list[dict[str, str]] = []
    for line in stderr.splitlines():
        m = _ARC_LINE_RE.match(line)
        if m:
            fields = dict(_KV_RE.findall(m.group(1)))
            results.append(fields)
    return results


def _compile_with_trace_arc(analyze_single, compile_and_run, tmp_path, src):
    """Shared pipeline: analyze → set trace_arc → codegen → compile → run → parse."""
    result = analyze_single("main", src)
    assert not result.has_errors(), result.diagnostics
    result.context.trace_arc = True

    from l0_backend import Backend

    c_code = Backend(result).generate()
    ok, stdout, stderr = compile_and_run(c_code, tmp_path)
    arc_lines = parse_arc_lines(stderr)
    return ok, stdout, stderr, arc_lines


# ---------------------------------------------------------------------------
# A – Static string noop
# ---------------------------------------------------------------------------


def test_trace_arc_static_string_noop(analyze_single, compile_and_run, tmp_path):
    """Static strings should produce only noop actions (no heap ops)."""
    ok, _stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;

        func main() -> int {
            let a: string = "hello";
            let b: string = a;
            return 0;
        }
        """,
    )
    assert ok, _stderr
    assert len(arc) > 0, "expected ARC trace events for static strings"
    for ev in arc:
        assert ev["kind"] == "static", f"unexpected heap event: {ev}"
        assert ev["action"] == "noop", f"expected noop for static: {ev}"


# ---------------------------------------------------------------------------
# B – Heap string lifecycle (concat → release → free)
# ---------------------------------------------------------------------------


def test_trace_arc_heap_string_lifecycle(analyze_single, compile_and_run, tmp_path):
    """A single heap string (from concat_s) must be freed with rc 1→0."""
    ok, _stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;
        import std.string;

        func main() -> int {
            let h: string = concat_s("a", "b");
            return 0;
        }
        """,
    )
    assert ok, _stderr

    heap_releases = [e for e in arc if e["kind"] == "heap" and e["op"] == "release"]
    frees = [e for e in heap_releases if e["action"] == "free"]
    assert len(frees) >= 1, f"expected at least one heap free, got: {heap_releases}"

    for f in frees:
        assert f["rc_before"] == "1"
        assert f["rc_after"] == "0"


# ---------------------------------------------------------------------------
# C – Copy-retain then release
# ---------------------------------------------------------------------------


def test_trace_arc_string_copy_retain_and_release(
    analyze_single, compile_and_run, tmp_path
):
    """Copying a heap string must retain (1→2), then release both (keep 2→1, free 1→0)."""
    ok, _stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;
        import std.string;

        func main() -> int {
            let a: string = concat_s("x", "y");
            let b: string = a;
            return 0;
        }
        """,
    )
    assert ok, _stderr

    heap = [e for e in arc if e["kind"] == "heap"]
    retains = [e for e in heap if e["op"] == "retain" and e["action"] == "retain"]
    assert any(
        e["rc_before"] == "1" and e["rc_after"] == "2" for e in retains
    ), f"expected retain 1→2: {retains}"

    releases = [e for e in heap if e["op"] == "release"]
    keeps = [e for e in releases if e["action"] == "keep"]
    frees = [e for e in releases if e["action"] == "free"]
    assert any(
        e["rc_before"] == "2" and e["rc_after"] == "1" for e in keeps
    ), f"expected keep 2→1: {keeps}"
    assert any(
        e["rc_before"] == "1" and e["rc_after"] == "0" for e in frees
    ), f"expected free 1→0: {frees}"


# ---------------------------------------------------------------------------
# D – Fanout: three references
# ---------------------------------------------------------------------------


def test_trace_arc_fanout_three_references(
    analyze_single, compile_and_run, tmp_path
):
    """Three aliases to one heap string: retain 1→2→3, then release 3→2→1→0."""
    ok, _stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;
        import std.string;

        func main() -> int {
            let a: string = concat_s("f", "o");
            let b: string = a;
            let c: string = a;
            return 0;
        }
        """,
    )
    assert ok, _stderr

    heap = [e for e in arc if e["kind"] == "heap"]
    retains = [e for e in heap if e["op"] == "retain" and e["action"] == "retain"]

    rc_afters = sorted(int(e["rc_after"]) for e in retains)
    assert 2 in rc_afters, f"expected retain to rc=2: {retains}"
    assert 3 in rc_afters, f"expected retain to rc=3: {retains}"

    releases = [e for e in heap if e["op"] == "release"]
    frees = [e for e in releases if e["action"] == "free"]
    assert any(
        e["rc_before"] == "1" and e["rc_after"] == "0" for e in frees
    ), f"expected final free 1→0: {frees}"


# ---------------------------------------------------------------------------
# E – Discarded concat freed immediately
# ---------------------------------------------------------------------------


def test_trace_arc_discarded_concat_freed(
    analyze_single, compile_and_run, tmp_path
):
    """A discarded call result (no binding) must still be freed."""
    ok, _stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;
        import std.string;

        func main() -> int {
            concat_s("a", "b");
            return 0;
        }
        """,
    )
    assert ok, _stderr

    heap = [e for e in arc if e["kind"] == "heap"]
    frees = [e for e in heap if e["op"] == "release" and e["action"] == "free"]
    assert len(frees) >= 1, f"expected discarded temp to be freed: {heap}"
    assert frees[0]["rc_before"] == "1"
    assert frees[0]["rc_after"] == "0"

    # No heap retains expected for a discarded temp.
    heap_retains = [
        e for e in heap if e["op"] == "retain" and e["action"] == "retain"
    ]
    assert len(heap_retains) == 0, f"unexpected heap retain: {heap_retains}"


# ---------------------------------------------------------------------------
# F – Struct with static string field drop
# ---------------------------------------------------------------------------


def test_trace_arc_struct_string_field_drop(
    analyze_single, compile_and_run, tmp_path
):
    """Dropping a struct with a static string field fires a static release noop."""
    ok, _stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;

        struct Box {
            s: string;
        }

        func main() -> int {
            let b: Box* = new Box("hello");
            drop b;
            return 0;
        }
        """,
    )
    assert ok, _stderr

    static_releases = [
        e for e in arc if e["kind"] == "static" and e["op"] == "release"
    ]
    assert any(
        e["action"] == "noop" for e in static_releases
    ), f"expected static release noop on struct drop: {arc}"


# ---------------------------------------------------------------------------
# F2 – Struct with heap string field drop
# ---------------------------------------------------------------------------


def test_trace_arc_struct_heap_string_field_drop(
    analyze_single, compile_and_run, tmp_path
):
    """Dropping a struct with a heap string field must free the string."""
    ok, _stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;
        import std.string;

        struct Box {
            s: string;
        }

        func main() -> int {
            let b: Box* = new Box(concat_s("he", "ap"));
            drop b;
            return 0;
        }
        """,
    )
    assert ok, _stderr

    heap_frees = [
        e for e in arc
        if e["kind"] == "heap" and e["op"] == "release" and e["action"] == "free"
    ]
    assert len(heap_frees) >= 1, f"expected heap free on struct drop: {arc}"
    assert heap_frees[-1]["rc_after"] == "0"


# ---------------------------------------------------------------------------
# G – Enum string variant cleanup
# ---------------------------------------------------------------------------


def test_trace_arc_enum_string_variant_cleanup(
    analyze_single, compile_and_run, tmp_path
):
    """A heap string inside an enum variant must be freed at scope exit."""
    ok, _stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;
        import std.string;

        enum E {
            Val(value: string);
            Empty;
        }

        func main() -> int {
            let e: E = Val(concat_s("v", "al"));
            return 0;
        }
        """,
    )
    assert ok, _stderr

    heap_frees = [
        e for e in arc
        if e["kind"] == "heap" and e["op"] == "release" and e["action"] == "free"
    ]
    assert len(heap_frees) >= 1, f"expected heap free for enum variant: {arc}"


# ---------------------------------------------------------------------------
# H – Optional string cleanup
# ---------------------------------------------------------------------------


def test_trace_arc_optional_string_cleanup(
    analyze_single, compile_and_run, tmp_path
):
    """A heap string wrapped in string? must be freed at scope exit."""
    ok, _stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;
        import std.string;

        func main() -> int {
            let v: string? = concat_s("o", "pt") as string?;
            return 0;
        }
        """,
    )
    assert ok, _stderr

    heap_frees = [
        e for e in arc
        if e["kind"] == "heap" and e["op"] == "release" and e["action"] == "free"
    ]
    assert len(heap_frees) >= 1, f"expected heap free for optional string: {arc}"


# ---------------------------------------------------------------------------
# H2 – Null optional: no heap releases
# ---------------------------------------------------------------------------


def test_trace_arc_null_optional_no_heap_release(
    analyze_single, compile_and_run, tmp_path
):
    """A null optional string must not produce any heap release events."""
    ok, _stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;

        func main() -> int {
            let v: string? = null;
            return 0;
        }
        """,
    )
    assert ok, _stderr

    heap_releases = [
        e for e in arc if e["kind"] == "heap" and e["op"] == "release"
    ]
    assert len(heap_releases) == 0, f"unexpected heap release for null optional: {heap_releases}"


# ---------------------------------------------------------------------------
# I – Nested concat: intermediary freed
# ---------------------------------------------------------------------------


def test_trace_arc_nested_concat_intermediary_freed(
    analyze_single, compile_and_run, tmp_path
):
    """Nested concat_s must free both the intermediary and the outer result."""
    ok, stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;
        import std.io;
        import std.string;

        func main() -> int {
            let x: string = concat_s("a", concat_s("b", "c"));
            printl_s(x);
            return 0;
        }
        """,
    )
    assert ok, _stderr
    assert stdout.strip() == "abc"

    heap_frees = [
        e for e in arc
        if e["kind"] == "heap" and e["op"] == "release" and e["action"] == "free"
    ]
    # At least 2 heap frees: the intermediary concat_s("b","c") and the outer result.
    assert len(heap_frees) >= 2, (
        f"expected >=2 heap frees (intermediary + final), got {len(heap_frees)}: {heap_frees}"
    )
    # All should be simple rc 1→0 frees (no shared references).
    for f in heap_frees:
        assert f["rc_before"] == "1" and f["rc_after"] == "0", (
            f"expected rc 1→0 free: {f}"
        )


def test_trace_arc_concat3_nested_argument_freed(
    analyze_single, compile_and_run, tmp_path
):
    """concat3_s-style nested argument temps must be freed on each call."""
    ok, stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;
        import std.io;
        import std.string;

        func concat3_s(a: string, b: string, c: string) -> string {
            return concat_s(concat_s(a, b), c);
        }

        func main() -> int {
            let x: string = concat3_s("a", "b", "c");
            let y: string = concat3_s("", "middle", "");
            printl_s(x);
            printl_s(y);
            return 0;
        }
        """,
    )
    assert ok, _stderr
    assert stdout.strip().splitlines() == ["abc", "middle"]

    heap_frees = [
        e for e in arc
        if e["kind"] == "heap" and e["op"] == "release" and e["action"] == "free"
    ]
    # Two concat3_s calls => each has one intermediary + one final heap string.
    assert len(heap_frees) >= 4, (
        f"expected >=4 heap frees (2 calls x intermediary+final), got {len(heap_frees)}: {heap_frees}"
    )
    for f in heap_frees:
        assert f["rc_before"] == "1" and f["rc_after"] == "0", (
            f"expected rc 1→0 free: {f}"
        )


# ---------------------------------------------------------------------------
# J – Return borrowed param retains
# ---------------------------------------------------------------------------


def test_trace_arc_return_borrowed_param_retains(
    analyze_single, compile_and_run, tmp_path
):
    """Returning a borrowed string param must retain it (1→2) for the caller."""
    ok, stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;
        import std.io;
        import std.string;

        func id_s(s: string) -> string {
            return s;
        }

        func main() -> int {
            let a: string = concat_s("i", "d");
            let b: string = id_s(a);
            printl_s(b);
            return 0;
        }
        """,
    )
    assert ok, _stderr
    assert stdout.strip() == "id"

    heap = [e for e in arc if e["kind"] == "heap"]
    retains = [e for e in heap if e["op"] == "retain" and e["action"] == "retain"]
    assert any(
        e["rc_before"] == "1" and e["rc_after"] == "2" for e in retains
    ), f"expected retain 1→2 for borrowed return: {retains}"

    releases = [e for e in heap if e["op"] == "release"]
    keeps = [e for e in releases if e["action"] == "keep"]
    frees = [e for e in releases if e["action"] == "free"]
    assert len(keeps) >= 1, f"expected at least one keep release: {releases}"
    assert len(frees) >= 1, f"expected at least one free release: {releases}"


# ---------------------------------------------------------------------------
# K – Leak-freedom balance (comprehensive)
# ---------------------------------------------------------------------------


def test_trace_arc_leak_freedom_balance(
    analyze_single, compile_and_run, tmp_path
):
    """
    Complex program exercising concat, copy, id_s, discard, and print.

    Every unique heap pointer must have ``action=free`` as its last event,
    and the number of free events must equal the number of unique heap pointers.
    """
    ok, stdout, _stderr, arc = _compile_with_trace_arc(
        analyze_single,
        compile_and_run,
        tmp_path,
        """
        module main;
        import std.io;
        import std.string;

        func id_s(s: string) -> string {
            return s;
        }

        func main() -> int {
            let a: string = concat_s("he", "llo");
            let b: string = a;
            let c: string = id_s(b);
            concat_s("dis", "card");
            printl_s(c);
            return 0;
        }
        """,
    )
    assert ok, _stderr
    assert stdout.strip() == "hello"

    # Group heap events by ptr.
    heap = [e for e in arc if e["kind"] == "heap"]
    by_ptr: dict[str, list[dict[str, str]]] = defaultdict(list)
    for ev in heap:
        by_ptr[ev["ptr"]].append(ev)

    assert len(by_ptr) > 0, "expected at least one heap pointer"

    # Every unique heap pointer must end with a free.
    for ptr, events in by_ptr.items():
        last = events[-1]
        assert last["action"] == "free", (
            f"ptr {ptr}: last action is {last['action']}, not free. events={events}"
        )

    # The total number of frees must equal the number of unique heap pointers.
    total_frees = sum(
        1 for ev in heap if ev["op"] == "release" and ev["action"] == "free"
    )
    assert total_frees == len(by_ptr), (
        f"free count ({total_frees}) != unique heap ptrs ({len(by_ptr)})"
    )
