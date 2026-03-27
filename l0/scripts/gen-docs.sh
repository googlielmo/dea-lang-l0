#!/bin/bash
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

set -euo pipefail

cd "$(dirname "$0")/.."

stable_pdf_name="dea_l0_api_reference.pdf"

show_usage() {
    cat <<'EOF'
Usage: ./scripts/gen-docs.sh [--pdf|--pdf-fast] [-v|--verbose] [docgen options...]

Wrapper around `python -m compiler.docgen.l0_docgen`.

Extra options:
  --pdf            Build `dea_l0_api_reference.pdf` from the generated LaTeX and copy it to `build/docs/pdf/`
                   or `<output-dir>/pdf/` when `--output-dir` is provided.
  --pdf-fast       Build a preview `dea_l0_api_reference.pdf` with a single `pdflatex` pass (faster, less complete references/index).
  -v, --verbose    Show docgen warnings and LaTeX build output directly.

Environment:
  L0_DOCS_RELEASE_TAG
                   Optional release tag to show on the PDF front matter title page, e.g.
                   `L0_DOCS_RELEASE_TAG=v0.9.9 ./scripts/gen-docs.sh --pdf-fast`.
EOF
}

run_logged() {
    local log_file=$1
    shift
    if (( verbose )); then
        "$@"
    else
        if ! "$@" >"$log_file" 2>&1; then
            keep_logs=1
            echo "Error: command failed: $*" >&2
            echo "Log saved to: $log_file" >&2
            cat "$log_file" >&2
            exit 1
        fi
    fi
}

sync_preview_dir() {
    local src_dir=$1
    local dst_dir=$2
    if [[ ! -d "$src_dir" ]]; then
        return
    fi
    mkdir -p "$(dirname "$dst_dir")"
    rm -rf "$dst_dir"
    cp -a "$src_dir" "$dst_dir"
}

if ! command -v doxygen >/dev/null 2>&1; then
    echo "Error: doxygen could not be found. Please install it."
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv could not be found. Please install it."
    exit 1
fi

if [ ! -d "../tools/m.css/documentation" ]; then
    echo "Error: vendored m.css checkout is missing at ../tools/m.css."
    exit 1
fi

build_pdf=0
build_pdf_fast=0
verbose=0
output_dir="build/docs"
html_only=0
markdown_only=0
latex_only=0
no_latex=0
docgen_args=()

while (($#)); do
    case "$1" in
        --pdf)
            build_pdf=1
            shift
            ;;
        --pdf-fast)
            build_pdf_fast=1
            shift
            ;;
        -v|--verbose)
            verbose=1
            shift
            ;;
        --output-dir)
            if (($# < 2)); then
                echo "Error: --output-dir requires a value." >&2
                exit 1
            fi
            output_dir=$2
            docgen_args+=("$1" "$2")
            shift 2
            ;;
        --output-dir=*)
            output_dir=${1#*=}
            docgen_args+=("$1")
            shift
            ;;
        --html-only)
            html_only=1
            docgen_args+=("$1")
            shift
            ;;
        --markdown-only)
            markdown_only=1
            docgen_args+=("$1")
            shift
            ;;
        --latex-only)
            latex_only=1
            docgen_args+=("$1")
            shift
            ;;
        --no-latex)
            no_latex=1
            docgen_args+=("$1")
            shift
            ;;
        -h|--help)
            show_usage
            uv run --group docs python -m compiler.docgen.l0_docgen --help
            exit 0
            ;;
        *)
            docgen_args+=("$1")
            shift
            ;;
    esac
done

if (( build_pdf )) && (( build_pdf_fast )); then
    echo "Error: --pdf and --pdf-fast are mutually exclusive." >&2
    exit 1
fi

if (( build_pdf || build_pdf_fast )) && (( html_only || markdown_only || no_latex )); then
    echo "Error: --pdf and --pdf-fast require LaTeX output. They cannot be combined with --html-only, --markdown-only, or --no-latex." >&2
    exit 1
fi

if (( build_pdf )) && ! command -v make >/dev/null 2>&1; then
    echo "Error: make could not be found. Please install it to build PDF output." >&2
    exit 1
fi

log_dir=$(mktemp -d "${TMPDIR:-/tmp}/gen-docs.XXXXXX")
keep_logs=0
cleanup() {
    if [[ -d "$log_dir" ]] && (( ! verbose )) && (( ! keep_logs )); then
        rm -rf "$log_dir"
    fi
}
trap cleanup EXIT

if [ "${#docgen_args[@]}" -gt 0 ]; then
    run_logged "$log_dir/l0_docgen.log" uv run --group docs python -m compiler.docgen.l0_docgen "${docgen_args[@]}"
else
    run_logged "$log_dir/l0_docgen.log" uv run --group docs python -m compiler.docgen.l0_docgen
fi

if (( build_pdf )); then
    latex_dir="${output_dir%/}/doxygen/latex"
    pdf_dir="${output_dir%/}/pdf"
    run_logged "$log_dir/latex-build.log" make -C "$latex_dir" LATEX_CMD="pdflatex -interaction=nonstopmode -halt-on-error"
    mkdir -p "$pdf_dir"
    cp "$latex_dir/refman.pdf" "$pdf_dir/$stable_pdf_name"
elif (( build_pdf_fast )); then
    latex_dir="${output_dir%/}/doxygen/latex"
    pdf_dir="${output_dir%/}/pdf"
    run_logged "$log_dir/latex-build.log" sh -c "cd \"$latex_dir\" && pdflatex -interaction=nonstopmode -halt-on-error refman"
    mkdir -p "$pdf_dir"
    cp "$latex_dir/refman.pdf" "$pdf_dir/$stable_pdf_name"
fi

preview_root="build/preview"
sync_preview_dir "${output_dir%/}/html" "${preview_root}/html"
sync_preview_dir "${output_dir%/}/markdown" "${preview_root}/markdown"
sync_preview_dir "${output_dir%/}/pdf" "${preview_root}/pdf"

undocumented_functions_report="${output_dir%/}/undocumented-functions.txt"
if [[ -f "$undocumented_functions_report" ]]; then
    if grep -E -v '^(#|$|No undocumented functions found\.)' "$undocumented_functions_report" >/dev/null; then
        echo "Undocumented functions report: $undocumented_functions_report"
    fi
fi
