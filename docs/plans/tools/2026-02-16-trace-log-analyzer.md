# Tool Implementation Plan

## Implement Stage 2 trace log analyzer for runtime issue detection

- Date: 2026-02-14
- Status: Closed (implemented)
- Title: Implement Stage 2 trace log analyzer for runtime issue detection
- Kind: Tooling
- Severity: Medium (improves debugging efficiency and regression detection)
- Stage: 2
- Subsystem: Tools
- Modules: `compiler/stage2_l0/check_trace_log.py`, `compiler/stage1_py/tests/cli/test_stage2_trace_log_checker.py`

## Summary

Add a standalone checker script that analyzes trace stderr logs produced by Stage 2 runs and exits non-zero only on
definite runtime problems (leaks, malformed critical events, panic actions, impossible balances).
Keep it independent of capture so it works on archived logs too.

## Public Interfaces / Types / CLI Additions

1. New script: compiler/stage2_l0/check_trace_log.py
2. CLI contract:
    1. ./compiler/stage2_l0/check_trace_log.py <trace_stderr.log>
    2. Optional flags:
        1. --triage (print leak clustering/examples for faster debugging)
        2. --max-details N (override default detail cap for errors/warnings/triage examples)
    3. Exit 0 when no definite issues are found.
    4. Exit 1 when definite issues are found.
    5. Exit 2 for usage/input errors (missing file, unreadable file).
3. Output contract:
    1. Human-readable summary to stdout.
    2. Sections: errors, warnings, stats.
    3. Deterministic wording for CI parsing (fixed prefixes like ERROR: and WARN:).

## Implementation Plan

1. Parse logic
    1. Read file line-by-line.
    2. Parse only lines starting with [l0][mem] or [l0][arc].
    3. Split key/value fields with regex compatible with current runtime format.
    4. Record line numbers for every parsed event for diagnostics.
2. Memory lifecycle checks ([l0][mem])
    1. Track object lifecycles from op=new_alloc action=ok ptr=....
    2. Close object lifecycles with op=drop action=free ptr=....
    3. Compatibility path: if a tracked new_alloc ptr is finalized by op=free action=call, decrement balance and emit
       a warning (preferred finalization remains drop/free).
    4. Error on negative balance for any pointer (free/drop without prior alloc in current log).
    5. Error on non-zero open object balances at end of file.
    6. Track string lifecycles from op=alloc_string ptr=....
    7. Close string lifecycles with op=free_string action=free ptr=....
    8. Treat free_string action=decrement-only as non-terminal (no lifecycle close).
    9. Error on negative string balance and on non-zero string balance at EOF.
3. ARC/runtime sanity checks ([l0][arc])
    1. Error if action starts with panic.
    2. Error if kind=heap op=release action=free has missing/invalid rc_before or rc_after.
    3. Error if that terminal free event does not end at rc_after=0.
4. Malformed critical-field checks
    1. Error when a lifecycle-relevant event (new_alloc, drop, alloc_string, free_string, heap free release) is missing
       ptr.
    2. Warning for non-critical malformed trace lines that are ignored.
5. Summary/reporting
    1. Print total parsed mem and arc events.
    2. Print per-op counts for quick triage.
    3. Print first N detailed errors/warnings with line numbers, then truncation note.
    4. With --triage, print:
        1. leaked object/string pointer counts,
        2. leaked object counts grouped by new_alloc bytes,
        3. per-pointer example rows (line/bytes context), capped by --max-details.
6. Docs integration
    1. Update compiler/stage2_l0/README.md with a “Check trace logs” section.
    2. Show workflow:
        1. Capture with run_parser_trace.sh.
        2. Analyze with check_trace_log.py.

## Test Cases and Scenarios

1. Unit/CLI tests in compiler/stage1_py/tests/cli/test_stage2_trace_log_checker.py (so they run in existing pytest
   path).
2. Test: clean balanced log returns exit 0.
3. Test: new_alloc without matching drop free returns exit 1 and reports leak pointer.
4. Test: alloc_string without matching terminal free_string action=free returns exit 1.
5. Test: free_string action=decrement-only alone does not close lifecycle and does not falsely pass a leaked allocation.
6. Test: drop free without prior new_alloc returns exit 1 (negative balance).
7. Test: ARC panic action triggers exit 1.
8. Test: heap free release with rc_after != 0 triggers exit 1.
9. Test: malformed required fields (ptr missing on critical events) triggers exit 1.
10. Smoke test: run checker on a real parser trace artifact from run_parser_trace.sh and assert the command executes
    and emits a structured report (stats/op_counts/errors/warnings), with exit code interpreted as analysis result.
11. Test: new_alloc finalized by mem op=free action=call returns exit 0 and emits a warning.

## Assumptions and Defaults

1. Scope is Stage 2 trace stderr logs only (not stdout).
2. The checker is standalone and does not invoke l0c itself.
3. Failure policy is “definite issues only”; suspicious heuristics are warnings, not hard failures.
4. Pointer reuse across time is supported via balance accounting (not naive set equality).
5. Runtime trace format remains key/value and line-oriented as currently emitted.
6. Current Stage 2 parser trace artifacts may still produce real leak-like error reports; this tool treats those as
   defects to investigate, not as expected-pass baseline.
