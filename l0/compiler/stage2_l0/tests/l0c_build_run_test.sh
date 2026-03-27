#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
FIXTURE_ROOT="$SCRIPT_DIR/fixtures/driver"
mkdir -p "$REPO_ROOT/build/tests"
WORK_DIR="$(mktemp -d "$REPO_ROOT/build/tests/l0_stage2_build_run_test.XXXXXX")"
BOOTSTRAP_PARENT="$REPO_ROOT/build/tests"
BOOTSTRAP_DIR=""

is_windows_host() {
    case "$(uname -s)" in
        CYGWIN*|MINGW*|MSYS*) return 0 ;;
    esac
    return 1
}

prepare_windows_runtime_bin() {
    local dst="$1"
    local compiler_path=""
    local toolchain_bin=""

    if ! is_windows_host; then
        return 0
    fi

    for candidate in gcc clang cc tcc; do
        if compiler_path="$(command -v "$candidate" 2>/dev/null)"; then
            toolchain_bin="$(dirname "$compiler_path")"
            break
        fi
    done

    [ -n "$toolchain_bin" ] || fail "expected a host C compiler on PATH while preparing Windows runtime DLLs"

    # Keep only runtime DLLs available so the native launcher still starts after
    # we hide the toolchain executables from PATH for the no-compiler probe.
    cp "$toolchain_bin"/*.dll "$dst"/ 2>/dev/null || true
}

native_path() {
    local path="$1"
    if is_windows_host; then
        cygpath -w "$path"
    else
        printf '%s\n' "$path"
    fi
}

stage2_launcher_path() {
    local base="$1"
    if is_windows_host && [ -f "$base.cmd" ]; then
        native_path "$base.cmd"
    else
        printf '%s\n' "$base"
    fi
}

normalize_diff_input() {
    local src="$1"
    local dst="$2"
    if is_windows_host; then
        tr -d '\r' <"$src" >"$dst"
    else
        cp "$src" "$dst"
    fi
}

c_output_path() {
    local output_path="$1"
    local dir_path
    local file_name
    dir_path="$(dirname "$output_path")"
    file_name="$(basename "$output_path")"
    case "$file_name" in
        *.*) file_name="${file_name%.*}.c" ;;
        *) file_name="${file_name}.c" ;;
    esac
    printf '%s/%s\n' "$dir_path" "$file_name"
}

cleanup() {
    rm -rf "$WORK_DIR"
    if [ -n "$BOOTSTRAP_DIR" ]; then
        rm -rf "$BOOTSTRAP_DIR"
    fi
}
trap cleanup EXIT

fail() {
    echo "l0c_build_run_test: FAIL: $1" >&2
    echo "l0c_build_run_test: work=$WORK_DIR" >&2
    if [ -n "$BOOTSTRAP_DIR" ]; then
        echo "l0c_build_run_test: bootstrap=$BOOTSTRAP_DIR" >&2
    fi
    exit 1
}

assert_file() {
    local path="$1"
    [ -f "$path" ] || fail "expected file: $path"
}

assert_no_file() {
    local path="$1"
    [ ! -e "$path" ] || fail "did not expect path: $path"
}

assert_contains() {
    local path="$1"
    local needle="$2"
    grep -F "$needle" "$path" >/dev/null || fail "expected '$needle' in $path"
}

assert_text_equals() {
    local path="$1"
    local expected="$2"
    local actual
    actual="$(cat "$path")"
    [ "$actual" = "$expected" ] || fail "unexpected content in $path"
}

dump_text_file() {
    local path="$1"
    if [ -f "$path" ]; then
        echo "l0c_build_run_test: ----- $path -----" >&2
        sed -n '1,200p' "$path" >&2 || true
    else
        echo "l0c_build_run_test: missing file for debug dump: $path" >&2
    fi
}

debug_no_cc_probe() {
    local isolated_bin="$WORK_DIR/empty-bin"

    echo "l0c_build_run_test: no-compiler probe diagnostics:" >&2
    echo "l0c_build_run_test: stage2_native=$STAGE2_NATIVE" >&2
    echo "l0c_build_run_test: isolated_bin=$isolated_bin" >&2
    if [ -d "$isolated_bin" ]; then
        echo "l0c_build_run_test: isolated bin listing:" >&2
        ls -la "$isolated_bin" >&2 || true
    fi

    if is_windows_host; then
        echo "l0c_build_run_test: SYSTEMROOT=${SYSTEMROOT:-}" >&2
        echo "l0c_build_run_test: COMSPEC=${COMSPEC:-}" >&2
        echo "l0c_build_run_test: WINDIR=${WINDIR:-}" >&2
        echo "l0c_build_run_test: OS=${OS:-}" >&2
        echo "l0c_build_run_test: copied runtime DLLs:" >&2
        find "$isolated_bin" -maxdepth 1 -name '*.dll' -print >&2 || true
        if command -v where.exe >/dev/null 2>&1; then
            for candidate in gcc clang cc tcc; do
                echo "l0c_build_run_test: where.exe $candidate" >&2
                env -u L0_CC -u CC -u Path PATH="$isolated_bin" SYSTEMROOT="${SYSTEMROOT:-}" COMSPEC="${COMSPEC:-}" WINDIR="${WINDIR:-}" OS="${OS:-}" where.exe "$candidate" >&2 || true
            done
        fi
    fi

    dump_text_file "$WORK_DIR/no_cc.log"
}

cd "$REPO_ROOT"
mkdir -p "$BOOTSTRAP_PARENT"
BOOTSTRAP_DIR="$(mktemp -d "$BOOTSTRAP_PARENT/l0_stage2_buildrun.XXXXXX")"
DEA_BUILD_DIR="${BOOTSTRAP_DIR#$REPO_ROOT/}" ./scripts/build-stage2-l0c.sh >/dev/null
STAGE2_L0C="$(stage2_launcher_path "$BOOTSTRAP_DIR/bin/l0c-stage2")"
STAGE2_NATIVE="$(native_path "$BOOTSTRAP_DIR/bin/l0c-stage2.native")"
OK_MAIN_BIN="$WORK_DIR/ok_main.bin"
BYTE_MAIN_BIN="$WORK_DIR/byte_main.bin"
if is_windows_host; then
    OK_MAIN_BIN="$OK_MAIN_BIN.exe"
    BYTE_MAIN_BIN="$BYTE_MAIN_BIN.exe"
fi

"$STAGE2_L0C" --build --keep-c -P "$(native_path "$FIXTURE_ROOT")" -o "$(native_path "$OK_MAIN_BIN")" ok_main >"$WORK_DIR/build_ok.log" 2>&1
assert_file "$OK_MAIN_BIN"
assert_file "$(c_output_path "$OK_MAIN_BIN")"
"$OK_MAIN_BIN" >"$WORK_DIR/ok_main.stdout" 2>"$WORK_DIR/ok_main.stderr"
assert_text_equals "$WORK_DIR/ok_main.stdout" ""

"$STAGE2_NATIVE" --run -P "$(native_path "$FIXTURE_ROOT")" argv_dump -- "two words" "rock'n'roll" >"$WORK_DIR/argv.out" 2>&1
cat >"$WORK_DIR/argv.expected" <<'EOF'
3
two words
rock'n'roll
EOF
tail -n 3 "$WORK_DIR/argv.out" >"$WORK_DIR/argv.tail"
normalize_diff_input "$WORK_DIR/argv.tail" "$WORK_DIR/argv.tail.normalized"
if ! diff -u "$WORK_DIR/argv.expected" "$WORK_DIR/argv.tail.normalized" >"$WORK_DIR/argv.diff"; then
    echo "l0c_build_run_test: argv diff:" >&2
    cat "$WORK_DIR/argv.diff" >&2
    echo "l0c_build_run_test: argv raw output (sed -n l):" >&2
    sed -n 'l' "$WORK_DIR/argv.out" >&2
    echo "l0c_build_run_test: argv tail raw output (sed -n l):" >&2
    sed -n 'l' "$WORK_DIR/argv.tail" >&2
    echo "l0c_build_run_test: argv normalized tail (sed -n l):" >&2
    sed -n 'l' "$WORK_DIR/argv.tail.normalized" >&2
    echo "l0c_build_run_test: argv tail bytes (od -An -tx1 -c):" >&2
    od -An -tx1 -c "$WORK_DIR/argv.tail" >&2
    fail "argv forwarding output mismatch"
fi

"$STAGE2_L0C" --run -P examples demo -- add 2 3 >"$WORK_DIR/demo.out" 2>&1
tail -n 1 "$WORK_DIR/demo.out" >"$WORK_DIR/demo.tail"
assert_text_equals "$WORK_DIR/demo.tail" "= 5"

set +e
"$STAGE2_L0C" --run -P "$(native_path "$FIXTURE_ROOT")" exit_seven >"$WORK_DIR/exit_seven.out" 2>&1
rc=$?
set -e
if [ "$rc" -eq 0 ]; then
    fail "expected exit_seven to return a non-zero exit code"
fi
[ "$rc" -eq 7 ] || fail "expected --run exit code 7"

"$STAGE2_L0C" --run --keep-c -P "$(native_path "$FIXTURE_ROOT")" -o "$(native_path "$WORK_DIR/kept-name")" ok_main >"$WORK_DIR/run_keep.log" 2>&1
assert_file "$WORK_DIR/kept-name.c"

"$STAGE2_L0C" --run -P "$(native_path "$FIXTURE_ROOT")" -o "$(native_path "$WORK_DIR/ignored-output")" ok_main >"$WORK_DIR/run_warn.log" 2>&1
assert_contains "$WORK_DIR/run_warn.log" "L0C-0017"
assert_no_file "$WORK_DIR/ignored-output"

mkdir "$WORK_DIR/empty-bin"
prepare_windows_runtime_bin "$WORK_DIR/empty-bin"
# On Windows runners, the inherited environment may expose the search path as `Path`
# even when this shell only mutates `PATH`. Clear both spellings before probing the
# native launcher so the no-compiler branch is exercised reliably. On Windows we
# preserve SYSTEMROOT/COMSPEC/WINDIR/OS and copy only runtime DLLs into the empty
# PATH directory so the native executable still starts without exposing compiler
# executables to `where.exe`.
if is_windows_host; then
    if env -u L0_CC -u CC -u Path PATH="$WORK_DIR/empty-bin" SYSTEMROOT="${SYSTEMROOT:-}" COMSPEC="${COMSPEC:-}" WINDIR="${WINDIR:-}" OS="${OS:-}" "$STAGE2_NATIVE" --build -P "$(native_path "$FIXTURE_ROOT")" ok_main >"$WORK_DIR/no_cc.log" 2>&1; then
        debug_no_cc_probe
        fail "expected no-compiler build to fail"
    fi
else
    if env -u L0_CC -u CC -u Path PATH="$WORK_DIR/empty-bin" "$STAGE2_NATIVE" --build -P "$(native_path "$FIXTURE_ROOT")" ok_main >"$WORK_DIR/no_cc.log" 2>&1; then
        debug_no_cc_probe
        fail "expected no-compiler build to fail"
    fi
fi
if ! grep -F "L0C-0009" "$WORK_DIR/no_cc.log" >/dev/null; then
    debug_no_cc_probe
    fail "expected 'L0C-0009' in $WORK_DIR/no_cc.log"
fi

if "$STAGE2_L0C" --build --c-compiler false -P "$(native_path "$FIXTURE_ROOT")" ok_main >"$WORK_DIR/compile_fail.log" 2>&1; then
    fail "expected explicit failing compiler to fail"
fi
assert_contains "$WORK_DIR/compile_fail.log" "L0C-0010"

if "$STAGE2_L0C" --build --runtime-lib "$(native_path "$WORK_DIR/missing-lib")" -P "$(native_path "$FIXTURE_ROOT")" ok_main >"$WORK_DIR/runtime_lib_missing.log" 2>&1; then
    fail "expected missing runtime-lib directory to fail"
fi
assert_contains "$WORK_DIR/runtime_lib_missing.log" "L0C-0014"

mkdir "$WORK_DIR/empty-lib"
if "$STAGE2_L0C" --build --runtime-lib "$(native_path "$WORK_DIR/empty-lib")" -P "$(native_path "$FIXTURE_ROOT")" ok_main >"$WORK_DIR/runtime_lib_empty.log" 2>&1; then
    fail "expected empty runtime-lib directory to fail"
fi
assert_contains "$WORK_DIR/runtime_lib_empty.log" "L0C-0015"

if "$STAGE2_L0C" --build -P "$(native_path "$FIXTURE_ROOT")" no_main >"$WORK_DIR/no_main.log" 2>&1; then
    fail "expected missing-main build to fail"
fi
assert_contains "$WORK_DIR/no_main.log" "L0C-0012"

"$STAGE2_L0C" --build --keep-c -P "$(native_path "$FIXTURE_ROOT")" -o "$(native_path "$BYTE_MAIN_BIN")" byte_main >"$WORK_DIR/byte_main.log" 2>&1
assert_contains "$WORK_DIR/byte_main.log" "L0C-0013"
assert_file "$BYTE_MAIN_BIN"
assert_file "$(c_output_path "$BYTE_MAIN_BIN")"

echo "l0c_build_run_test: PASS"
