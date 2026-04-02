.DEFAULT_GOAL := help

VENV_DIR_REL := ../.venv
VENV_DIR := $(abspath $(VENV_DIR_REL))

ifeq ($(OS),Windows_NT)
VENV_PYTHON_DEFAULT := $(VENV_DIR)/Scripts/python.exe
else
VENV_PYTHON_DEFAULT := $(VENV_DIR)/bin/python
endif

HOST_PYTHON ?= $(shell if command -v python3 >/dev/null 2>&1; then printf '%s' python3; else printf '%s' python; fi)
VENV_PYTHON := $(shell if [ -x "$(VENV_DIR)/bin/python" ]; then printf '%s' "$(VENV_DIR)/bin/python"; elif [ -x "$(VENV_DIR)/Scripts/python.exe" ]; then printf '%s' "$(VENV_DIR)/Scripts/python.exe"; else printf '%s' $(VENV_PYTHON_DEFAULT); fi)
PYTHON ?= $(shell if [ -x "$(VENV_DIR)/bin/python" ]; then printf '%s' "$(VENV_DIR)/bin/python"; elif [ -x "$(VENV_DIR)/Scripts/python.exe" ]; then printf '%s' "$(VENV_DIR)/Scripts/python.exe"; else printf '%s' $(HOST_PYTHON); fi)
L1_BUILD_DIR ?= build/l1
VENV_UV_FLAGS := --quiet
VENV_PIP_FLAGS := --quiet --disable-pip-version-check
VENV_QUIET_LABEL := (quiet)

PIP_DEPS_CMD = import tomllib,pathlib;\
	g=tomllib.loads(pathlib.Path('pyproject.toml').read_text()).get('dependency-groups',{});\
	print(' '.join(d for d in g.get('dev',[])+g.get('docs',[]) if isinstance(d,str)))

.PHONY: help _check-python venv build-stage1 test-stage1 print-l1-build-dir clean

help:
	@printf '%s\n' \
		'Dea/L1 bootstrap workflow' \
		'' \
		'Targets:' \
		'  venv               Create or reuse the shared monorepo `../.venv`.' \
		'  build-stage1       Build the repo-local L1 Stage 1 compiler under `build/l1/bin`.' \
		'  test-stage1        Run the L1 Stage 1 `.l0` implementation test suite with the built repo-local compiler.' \
		'  clean              Remove repo-local build artifacts under `build/*`.' \
		'' \
		'Variables:' \
		'  L1_BUILD_DIR=build/l1' \
		'                     Repo-local L1 build root.' \
		'  L1_BOOTSTRAP_L0C=<path>' \
		'                     Explicit upstream L0 Stage 2 compiler wrapper or native binary.' \
		'  TESTS=""' \
		'                     Optional Stage 1 test names for `test-stage1`.' \
		'' \
		'Default local bootstrap flow:' \
		'  1. `make -C ../l0 use-dev-stage2`' \
		'  2. `make build-stage1`' \
		'  3. `source build/l1/bin/l1-env.sh` then run `l1c --help`.'

_check-python:
	@$(PYTHON) -c "import sys; sys.exit(0 if sys.version_info >= (3, 14) else 1)" 2>/dev/null \
		|| { printf 'error: Python 3.14+ is required (found: %s)\n' \
			"$$($(PYTHON) -c 'import sys; print(".".join(map(str,sys.version_info[:3])))' 2>/dev/null || echo 'none')" >&2; exit 1; }

venv: _check-python
	@if command -v uv >/dev/null 2>&1; then \
		if [ -x "$(VENV_PYTHON)" ]; then \
			printf '%s\n' 'make venv: syncing existing ../.venv with uv $(VENV_QUIET_LABEL)'; \
		fi; \
		UV_PROJECT_ENVIRONMENT="$(VENV_DIR)" uv sync $(VENV_UV_FLAGS) --group dev --group docs; \
	elif [ -x "$(VENV_PYTHON)" ]; then \
		printf '%s\n' 'make venv: refreshing existing ../.venv with pip $(VENV_QUIET_LABEL)'; \
		"$(VENV_PYTHON)" -m pip install $(VENV_PIP_FLAGS) $$("$(VENV_PYTHON)" -c "$(PIP_DEPS_CMD)"); \
	else \
		$(PYTHON) -m venv "$(VENV_DIR)"; \
		_vp="$$(if [ -x "$(VENV_DIR)/bin/python" ]; then printf '%s' "$(VENV_DIR)/bin/python"; else printf '%s' "$(VENV_DIR)/Scripts/python.exe"; fi)"; \
		"$$_vp" -m pip install $(VENV_PIP_FLAGS) $$("$$_vp" -c "$(PIP_DEPS_CMD)"); \
	fi

build-stage1: venv
	L1_BUILD_DIR="$(L1_BUILD_DIR)" "$(PYTHON)" ./scripts/build_stage1_l1c.py
	@printf 'Repo-local L1 Stage 1 compiler version:\n'
	@"$(L1_BUILD_DIR)/bin/l1c-stage1" --version

test-stage1: venv build-stage1
	L1_BUILD_DIR="$(L1_BUILD_DIR)" "$(VENV_PYTHON)" ./compiler/stage1_l0/run_tests.py $(TESTS)

print-l1-build-dir:
	@printf '%s\n' "$(L1_BUILD_DIR)"

clean:
	rm -rf ./build/*
	rm -f ./a.out ./a.exe
	rm -f ./compiler/stage1_l0/a.out ./compiler/stage1_l0/a.exe
	rm -f ./compiler/stage1_l0/tests/.tmp*
