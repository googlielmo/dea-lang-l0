#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Regression coverage for monorepo release-tag policy wiring."""

from __future__ import annotations

from pathlib import Path


def resolve_workflow_root() -> Path | None:
    start = Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        if (candidate / ".github" / "workflows" / "l0-release.yml").is_file():
            return candidate
    return None


def resolve_monorepo_root(workflow_root: Path | None) -> Path | None:
    if workflow_root is None:
        return None
    for candidate in (workflow_root, *workflow_root.parents):
        if (candidate / "MONOREPO.md").is_file():
            return candidate
    return None


WORKFLOW_ROOT = resolve_workflow_root()
MONOREPO_ROOT = resolve_monorepo_root(WORKFLOW_ROOT)


def fail(message: str) -> None:
    raise SystemExit(f"test_release_tag_policy: FAIL: {message}")


def read_text(path: str) -> str:
    if WORKFLOW_ROOT is None:
        fail(f"workflow root unavailable for {path}")
    return (WORKFLOW_ROOT / path).read_text(encoding="utf-8")


def read_monorepo_text(path: str) -> str:
    if MONOREPO_ROOT is None:
        fail(f"monorepo root unavailable for {path}")
    return (MONOREPO_ROOT / path).read_text(encoding="utf-8")


def assert_contains(text: str, needle: str, *, context: str) -> None:
    if needle not in text:
        fail(f"missing {needle!r} in {context}")


def check_release_workflow() -> None:
    text = read_text(".github/workflows/l0-release.yml")
    assert_contains(text, '- "l0-v*"', context="l0-release.yml")
    assert_contains(text, 'export DEA_DIST_VERSION="${RELEASE_VERSION#l0-v}"', context="l0-release.yml")
    assert_contains(text, "name: dea-l0-dist-${{ matrix.os }}-${{ matrix.arch }}", context="l0-release.yml")
    assert_contains(text, "pattern: dea-l0-dist-*", context="l0-release.yml")
    assert_contains(text, "name: github-pages", context="l0-release.yml")
    assert_contains(text, "uses: actions/deploy-pages@v4", context="l0-release.yml")
    assert_contains(text, "name: docs-markdown", context="l0-release.yml")
    assert_contains(text, "name: blog-export", context="l0-release.yml")
    assert_contains(text, 'gh release upload "$CURRENT_TAG" blog-export.tar.gz --clobber --repo "$GITHUB_REPOSITORY"', context="l0-release.yml")
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
    assert_contains(text, 'export DEA_DIST_VERSION="${SNAPSHOT_VERSION#l0-}"', context="l0-snapshot.yml")
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
    assert_contains(text, "RELEASE_TAG: ${{ github.event.release.tag_name }}", context="l0-docs-publish.yml")


def check_docs() -> None:
    if MONOREPO_ROOT is None:
        return

    monorepo = read_monorepo_text("MONOREPO.md")
    assert_contains(monorepo, "Pre-monorepo history keeps its original bare tags.", context="MONOREPO.md")
    assert_contains(monorepo, "`v0.9.0`, `v0.9.1`, and older", context="MONOREPO.md")
    assert_contains(monorepo, "`l0-vX.Y.Z`", context="MONOREPO.md")
    assert_contains(monorepo, "`l1-vX.Y.Z`", context="MONOREPO.md")

    readme = read_monorepo_text("README.md")
    assert_contains(readme, "Pre-monorepo bare tags such as `v0.9.0` and `v0.9.1` remain historical", context="README.md")
    assert_contains(readme, "current L0 releases use `l0-vX.Y.Z`", context="README.md")


def main() -> int:
    if WORKFLOW_ROOT is None:
        print("test_release_tag_policy: SKIP (workflow files unavailable in this checkout)")
        return 0

    check_release_workflow()
    check_snapshot_workflow()
    check_docs_publish_workflow()
    check_docs()
    print("test_release_tag_policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
