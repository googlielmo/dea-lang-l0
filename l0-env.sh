#!/usr/bin/env bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

script_src="${BASH_SOURCE[0]-}"
if [[ -z "${script_src}" && -n "${ZSH_VERSION-}" ]]; then
    script_src="${(%):-%N}"
fi

sourced=0
if [[ -n "${BASH_VERSION-}" && "${BASH_SOURCE[0]-}" != "${0}" ]]; then
    sourced=1
fi
if [[ "${sourced}" -eq 0 && -n "${ZSH_VERSION-}" && "${ZSH_EVAL_CONTEXT-}" == *:file ]]; then
    sourced=1
fi

if [[ -z "${script_src}" || "${sourced}" -eq 0 ]]; then
    echo "This script must be sourced: source ./l0-env.sh" >&2
    return 1 2>/dev/null || exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${script_src}")" && pwd -P)"
export L0_HOME="${SCRIPT_DIR}/compiler/stage1_py"

case ":${PATH}:" in
    *":${SCRIPT_DIR}:"*) ;;
    *) export PATH="${PATH}:${SCRIPT_DIR}" ;;
esac

export L0_CC="clang"