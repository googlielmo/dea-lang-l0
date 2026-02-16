#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from textwrap import dedent

TRACE_RE = re.compile(r"^\[l0\]\[(mem|arc)\]\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")


def _parse_events(text: str) -> tuple[list[dict[str, str]], list[str]]:
    events: list[dict[str, str]] = []
    warnings: list[str] = []

    normalized = dedent(text)

    for line_no, raw in enumerate(normalized.splitlines(), start=1):
        m = TRACE_RE.match(raw.lstrip())
        if not m:
            continue

        family = m.group(1)
        payload = m.group(2)
        fields = dict(KV_RE.findall(payload))
        event = {"family": family, "line_no": str(line_no), "raw": raw}
        event.update(fields)
        events.append(event)

        if "op" not in fields:
            warnings.append(f"line {line_no}: trace line missing op=..., ignored for op-based checks")

    return events, warnings


def _validate_events(events: list[dict[str, str]]) -> tuple[list[str], list[str], dict[str, int], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    op_counts: Counter[str] = Counter()

    obj_balance: defaultdict[str, int] = defaultdict(int)
    str_balance: defaultdict[str, int] = defaultdict(int)
    obj_new_meta: dict[str, dict[str, str]] = {}
    obj_last_ptr_line: dict[str, str] = {}
    str_alloc_line: dict[str, str] = {}
    str_last_ptr_line: dict[str, str] = {}

    for ev in events:
        family = ev["family"]
        line_no = ev["line_no"]
        op = ev.get("op")
        action = ev.get("action")
        ptr = ev.get("ptr")

        if op:
            op_counts[f"{family}:{op}"] += 1

        if family == "mem":
            if ptr:
                obj_last_ptr_line[ptr] = line_no
                str_last_ptr_line[ptr] = line_no

            if op in {"new_alloc", "drop", "alloc_string", "free_string"} and not ptr:
                errors.append(f"line {line_no}: mem op={op} is missing ptr")
                continue

            if op == "new_alloc" and action == "ok":
                obj_balance[ptr] += 1  # type: ignore[index]
                obj_new_meta[ptr] = {
                    "new_line": line_no,
                    "bytes": ev.get("bytes", "?"),
                }
            elif op == "drop" and action == "free":
                obj_balance[ptr] -= 1  # type: ignore[index]
                if obj_balance[ptr] < 0:  # type: ignore[index]
                    errors.append(
                        f"line {line_no}: drop/free for ptr={ptr} without matching new_alloc in this log"
                    )
            elif op == "free" and action == "call" and ptr:
                # Compatibility path: some object pointers may be finalized by direct free().
                # Treat it as a release for balance accounting, but surface it as a warning.
                if obj_balance[ptr] > 0:
                    obj_balance[ptr] -= 1
                    warnings.append(
                        f"line {line_no}: new_alloc ptr={ptr} released via mem op=free action=call (preferred: drop/free)"
                    )
            elif op == "alloc_string":
                str_balance[ptr] += 1  # type: ignore[index]
                if ptr not in str_alloc_line:
                    str_alloc_line[ptr] = line_no
            elif op == "free_string" and action == "free":
                str_balance[ptr] -= 1  # type: ignore[index]
                if str_balance[ptr] < 0:  # type: ignore[index]
                    errors.append(
                        f"line {line_no}: free_string/free for ptr={ptr} without matching alloc_string in this log"
                    )
            elif op == "free_string" and action == "decrement-only":
                pass
            elif op == "free_string" and action:
                warnings.append(f"line {line_no}: free_string has uncommon action={action}")

        if family == "arc":
            if action and action.startswith("panic"):
                errors.append(f"line {line_no}: arc panic action detected ({action})")

            is_heap_terminal_free = ev.get("kind") == "heap" and op == "release" and action == "free"
            if is_heap_terminal_free:
                if not ptr:
                    errors.append(f"line {line_no}: arc heap free release is missing ptr")
                    continue

                rc_before = ev.get("rc_before")
                rc_after = ev.get("rc_after")
                if rc_before is None or rc_after is None:
                    errors.append(f"line {line_no}: arc heap free release missing rc_before/rc_after")
                    continue

                try:
                    int(rc_before)
                    rc_after_i = int(rc_after)
                except ValueError:
                    errors.append(
                        f"line {line_no}: arc heap free release has non-integer rc values rc_before={rc_before} rc_after={rc_after}"
                    )
                    continue

                if rc_after_i != 0:
                    errors.append(
                        f"line {line_no}: arc heap free release must end at rc_after=0, got rc_after={rc_after_i}"
                    )

    leaked_objects: list[dict[str, str]] = []
    leaked_strings: list[dict[str, str]] = []
    leaked_object_bytes: Counter[str] = Counter()

    for ptr, bal in obj_balance.items():
        if bal != 0:
            errors.append(f"object leak balance for ptr={ptr}: remaining={bal} (new_alloc vs drop/free mismatch)")
            if bal > 0:
                meta = obj_new_meta.get(ptr, {})
                obj_bytes = meta.get("bytes", "?")
                leaked_object_bytes[obj_bytes] += 1
                leaked_objects.append(
                    {
                        "ptr": ptr,
                        "remaining": str(bal),
                        "new_line": meta.get("new_line", "?"),
                        "bytes": obj_bytes,
                        "last_ptr_line": obj_last_ptr_line.get(ptr, "?"),
                    }
                )
    for ptr, bal in str_balance.items():
        if bal != 0:
            errors.append(
                f"string leak balance for ptr={ptr}: remaining={bal} (alloc_string vs free_string/free mismatch)"
            )
            if bal > 0:
                leaked_strings.append(
                    {
                        "ptr": ptr,
                        "remaining": str(bal),
                        "alloc_line": str_alloc_line.get(ptr, "?"),
                        "last_ptr_line": str_last_ptr_line.get(ptr, "?"),
                    }
                )

    triage = {
        "leaked_objects": sorted(
            leaked_objects,
            key=lambda item: int(item["new_line"]) if item["new_line"].isdigit() else 10**9,
        ),
        "leaked_strings": sorted(
            leaked_strings,
            key=lambda item: int(item["alloc_line"]) if item["alloc_line"].isdigit() else 10**9,
        ),
        "leaked_object_bytes": dict(leaked_object_bytes),
    }

    return errors, warnings, dict(op_counts), triage


def _print_report(
    events: list[dict[str, str]],
    parse_warnings: list[str],
    errors: list[str],
    warnings: list[str],
    op_counts: dict[str, int],
    triage: dict,
    max_details: int,
    show_triage: bool,
) -> None:
    mem_count = sum(1 for e in events if e["family"] == "mem")
    arc_count = sum(1 for e in events if e["family"] == "arc")
    total_warnings = parse_warnings + warnings

    print("stats:")
    print(f"  mem_events={mem_count}")
    print(f"  arc_events={arc_count}")
    print(f"  total_events={len(events)}")
    print(f"  errors={len(errors)}")
    print(f"  warnings={len(total_warnings)}")

    if op_counts:
        print("op_counts:")
        for key in sorted(op_counts.keys()):
            print(f"  {key}={op_counts[key]}")

    if errors:
        print("errors:")
        for msg in errors[:max_details]:
            print(f"ERROR: {msg}")
        if len(errors) > max_details:
            print(f"ERROR: ... {len(errors) - max_details} more")

    if total_warnings:
        print("warnings:")
        for msg in total_warnings[:max_details]:
            print(f"WARN: {msg}")
        if len(total_warnings) > max_details:
            print(f"WARN: ... {len(total_warnings) - max_details} more")

    if show_triage:
        leaked_objects = triage.get("leaked_objects", [])
        leaked_strings = triage.get("leaked_strings", [])
        leaked_object_bytes = triage.get("leaked_object_bytes", {})

        print("triage:")
        print(f"  leaked_object_ptrs={len(leaked_objects)}")
        print(f"  leaked_string_ptrs={len(leaked_strings)}")

        if leaked_object_bytes:
            print("  leaked_object_bytes:")
            for b, count in sorted(
                leaked_object_bytes.items(),
                key=lambda item: (-item[1], item[0]),
            ):
                print(f"    bytes={b} count={count}")

        if leaked_objects:
            print("  leaked_object_examples:")
            for item in leaked_objects[:max_details]:
                print(
                    "    "
                    f"ptr={item['ptr']} remaining={item['remaining']} bytes={item['bytes']} "
                    f"new_line={item['new_line']} last_ptr_line={item['last_ptr_line']}"
                )
            if len(leaked_objects) > max_details:
                print(f"    ... {len(leaked_objects) - max_details} more")

        if leaked_strings:
            print("  leaked_string_examples:")
            for item in leaked_strings[:max_details]:
                print(
                    "    "
                    f"ptr={item['ptr']} remaining={item['remaining']} "
                    f"alloc_line={item['alloc_line']} last_ptr_line={item['last_ptr_line']}"
                )
            if len(leaked_strings) > max_details:
                print(f"    ... {len(leaked_strings) - max_details} more")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=Path(sys.argv[0]).name,
        description="Analyze Stage 2 trace stderr logs for definite runtime issues.",
    )
    parser.add_argument("trace_file", help="Path to trace stderr log file")
    parser.add_argument(
        "--max-details",
        type=int,
        default=20,
        help="Maximum number of error/warning/triage detail lines to print (default: 20)",
    )
    parser.add_argument(
        "--triage",
        action="store_true",
        help="Print leak triage details (leak counts by size and pointer examples)",
    )
    return parser


def main(argv: list[str]) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv[1:])

    if args.max_details < 1:
        print("error: --max-details must be >= 1")
        return 2

    trace_path = Path(args.trace_file)
    if not trace_path.exists() or not trace_path.is_file():
        print(f"error: trace file not found: {trace_path}")
        return 2

    try:
        text = trace_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: failed to read trace file {trace_path}: {exc}")
        return 2

    events, parse_warnings = _parse_events(text)
    errors, warnings, op_counts, triage = _validate_events(events)
    _print_report(
        events,
        parse_warnings,
        errors,
        warnings,
        op_counts,
        triage,
        max_details=args.max_details,
        show_triage=args.triage,
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
