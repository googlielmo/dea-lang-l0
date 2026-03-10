#!/usr/bin/env bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
DIST_DIR_INPUT="${DIST_DIR:-build/stage2}"

fail() {
    echo "build-stage2-l0c: $1" >&2
    exit 1
}

if [[ "${DIST_DIR_INPUT}" = /* ]]; then
    DIST_DIR_ABS="${DIST_DIR_INPUT}"
else
    DIST_DIR_ABS="${REPO_ROOT}/${DIST_DIR_INPUT}"
fi

DIST_PARENT="$(dirname -- "${DIST_DIR_ABS}")"
mkdir -p "${DIST_PARENT}"
DIST_DIR_ABS="$(cd -- "${DIST_PARENT}" && pwd -P)/$(basename -- "${DIST_DIR_ABS}")"

case "${DIST_DIR_ABS}" in
    "${REPO_ROOT}"|"${REPO_ROOT}"/*) ;;
    *)
        fail "DIST_DIR must resolve inside the repository: ${DIST_DIR_ABS}"
        ;;
esac

BIN_DIR="${DIST_DIR_ABS}/bin"
NATIVE_BIN="${BIN_DIR}/l0c-stage2.native"
C_OUTPUT="${BIN_DIR}/l0c-stage2.c"
WRAPPER_BIN="${BIN_DIR}/l0c-stage2"

mkdir -p "${BIN_DIR}"

BUILD_ARGS=(
    --build
    -P compiler/stage2_l0/src
    -o "${NATIVE_BIN}"
    l0c
)

if [[ "${KEEP_C:-0}" = "1" ]]; then
    BUILD_ARGS=(--keep-c "${BUILD_ARGS[@]}")
else
    rm -f "${C_OUTPUT}"
fi

(
    cd -- "${REPO_ROOT}"
    ./l0c "${BUILD_ARGS[@]}"
)

if [[ "${KEEP_C:-0}" != "1" ]]; then
    rm -f "${C_OUTPUT}"
fi

REPO_RELATIVE_FROM_BIN="$(python3 -c 'import os, sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "${REPO_ROOT}" "${BIN_DIR}")"

cat > "${WRAPPER_BIN}" <<EOF
#!/bin/sh
set -eu

script_dir=\$(CDPATH= cd -- "\$(dirname -- "\$0")" && pwd -P)
repo_root=\$(CDPATH= cd -- "\${script_dir}/${REPO_RELATIVE_FROM_BIN}" && pwd -P)

if [ -z "\${L0_HOME:-}" ]; then
    export L0_HOME="\${repo_root}/compiler"
fi

exec "\${script_dir}/l0c-stage2.native" "\$@"
EOF

chmod +x "${NATIVE_BIN}" "${WRAPPER_BIN}"

echo "build-stage2-l0c: wrote ${WRAPPER_BIN}"
echo "build-stage2-l0c: wrote ${NATIVE_BIN}"
if [[ "${KEEP_C:-0}" = "1" ]]; then
    echo "build-stage2-l0c: wrote ${C_OUTPUT}"
fi
