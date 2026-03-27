#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Regression coverage for monorepo release-tag policy wiring."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def fail(message: str) -> None:
    raise SystemExit(f"test_release_tag_policy: FAIL: {message}")


def read_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def assert_contains(text: str, needle: str, *, context: str) -> None:
    if needle not in text:
        fail(f"missing {needle!r} in {context}")


def check_release_workflow() -> None:
    text = read_text(".github/workflows/l0-release.yml")
    assert_contains(text, '- "l0-v*"', context="l0-release.yml")
    assert_contains(text, '${RELEASE_VERSION#l0-v}', context="l0-release.yml")
    assert_contains(text, "name: dea-l0-dist-${{ matrix.os }}-${{ matrix.arch }}", context="l0-release.yml")
    assert_contains(text, "pattern: dea-l0-dist-*", context="l0-release.yml")
    assert_contains(
        text,
        "prev_tag=\"$(git tag --merged HEAD --sort=-v:refname | grep '^l0-v' | grep -Fxv \"$CURRENT_TAG\" | head -n 1 || true)\"",
        context="l0-release.yml",
    )
    assert_contains(
        text,
        "prev_tag=\"$(git tag --merged HEAD --sort=-v:refname | grep -E '^v[0-9]+\\.[0-9]+\\.[0-9]+$' | head -n 1 || true)\"",
        context="l0-release.yml",
    )


def check_snapshot_workflow() -> None:
    text = read_text(".github/workflows/l0-snapshot.yml")
    assert_contains(text, 'snapshot_version="l0-snapshot-${stamp}-${short_hash}"', context="l0-snapshot.yml")
    assert_contains(text, "name: dea-l0-dist-${{ matrix.os }}-${{ matrix.arch }}", context="l0-snapshot.yml")
    assert_contains(text, "pattern: dea-l0-dist-*", context="l0-snapshot.yml")
    assert_contains(
        text,
        "prev_tag=\"$(git tag --merged HEAD --sort=-v:refname | grep -E '^(l0-v|l0-snapshot-)' | grep -Fxv \"$CURRENT_TAG\" | head -n 1 || true)\"",
        context="l0-snapshot.yml",
    )
    assert_contains(
        text,
        "prev_tag=\"$(git tag --merged HEAD --sort=-v:refname | grep -E '^v[0-9]+\\.[0-9]+\\.[0-9]+$' | head -n 1 || true)\"",
        context="l0-snapshot.yml",
    )


def check_docs_publish_workflow() -> None:
    text = read_text(".github/workflows/l0-docs-publish.yml")
    assert_contains(text, "startsWith(github.event.release.tag_name, 'l0-v')", context="l0-docs-publish.yml")
    assert_contains(text, "git describe --tags --abbrev=0 --match 'l0-v*'", context="l0-docs-publish.yml")


def check_docs() -> None:
    monorepo = read_text("MONOREPO.md")
    assert_contains(monorepo, "Pre-monorepo history keeps its original bare tags.", context="MONOREPO.md")
    assert_contains(monorepo, "`v0.9.0`, `v0.9.1`, and older", context="MONOREPO.md")
    assert_contains(monorepo, "`l0-vX.Y.Z`", context="MONOREPO.md")
    assert_contains(monorepo, "`l1-vX.Y.Z`", context="MONOREPO.md")

    readme = read_text("README.md")
    assert_contains(readme, "Pre-monorepo bare tags such as `v0.9.0` and `v0.9.1` remain historical", context="README.md")
    assert_contains(readme, "current L0 releases use `l0-vX.Y.Z`", context="README.md")


def main() -> int:
    check_release_workflow()
    check_snapshot_workflow()
    check_docs_publish_workflow()
    check_docs()
    print("test_release_tag_policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
