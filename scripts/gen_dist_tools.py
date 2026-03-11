#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
#

"""Generate repo-local dist tooling artifacts."""

from __future__ import annotations

import argparse
import sys

from dist_tools_lib import normalize_dist_dir, remove_dist_tree, set_alias, write_env_script, write_stage1_wrapper, write_stage2_wrapper


def add_dist_dir_arg(parser: argparse.ArgumentParser) -> None:
    """Attach the shared dist-dir option to one parser."""

    parser.add_argument("--dist-dir", required=True, help="Repo-local dist directory to generate into.")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Generate repo-local dist wrapper artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    write_stage1 = subparsers.add_parser("write-stage1-wrapper", help="Write `bin/l0c-stage1`.")
    add_dist_dir_arg(write_stage1)

    write_stage2 = subparsers.add_parser("write-stage2-wrapper", help="Write `bin/l0c-stage2`.")
    add_dist_dir_arg(write_stage2)

    write_env = subparsers.add_parser("write-env-script", help="Write `bin/l0-env.sh`.")
    add_dist_dir_arg(write_env)

    alias_parser = subparsers.add_parser("set-alias", help="Point `bin/l0c` at one stage wrapper.")
    add_dist_dir_arg(alias_parser)
    alias_parser.add_argument("--stage", choices=("stage1", "stage2"), required=True)

    clean_parser = subparsers.add_parser("clean-dist", help="Delete one validated dist tree.")
    add_dist_dir_arg(clean_parser)

    return parser.parse_args()


def main() -> int:
    """Program entrypoint."""

    args = parse_args()
    try:
        layout = normalize_dist_dir(args.dist_dir)
        if args.command == "write-stage1-wrapper":
            path = write_stage1_wrapper(layout)
            print(f"gen-dist-tools: wrote {path}")
            return 0
        if args.command == "write-stage2-wrapper":
            path = write_stage2_wrapper(layout)
            print(f"gen-dist-tools: wrote {path}")
            return 0
        if args.command == "write-env-script":
            path = write_env_script(layout)
            print(f"gen-dist-tools: wrote {path}")
            return 0
        if args.command == "set-alias":
            path = set_alias(layout, args.stage)
            print(f"gen-dist-tools: linked {path} -> {path.readlink()}")
            return 0
        if args.command == "clean-dist":
            remove_dist_tree(layout)
            print(f"gen-dist-tools: removed {layout.dist_dir}")
            return 0
        raise AssertionError(f"unhandled command: {args.command}")
    except ValueError as exc:
        print(f"gen-dist-tools: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
