---
name: finalize-dea-work
description: Finalize Dea repo work by checking plans/docs/tests, staging only intended files, running level-appropriate validation and pre-commit, and committing with the required Dea L0/L1 message format.
---

### Finalize and commit Dea work

Use this skill when the user asks to finalize, close plans, commit changes, prepare a commit, or package completed Dea
work.

## Required context

1. Read root `CLAUDE.md` first.
2. If touched paths are under `l0/`, read `l0/CLAUDE.md`.
3. If touched paths are under `l1/`, read `l1/CLAUDE.md`.
4. Check `git status --short` before staging. Never stage unrelated user files.

## Finalization workflow

1. Review the diff and classify the work:
   - one cohesive change: one commit
   - separable implementation/docs/tooling pieces: two or three commits
   - unrelated work: leave it unstaged and tell the user
2. Finish lifecycle artifacts before committing:
   - active plans that are complete move to `work/plans/<kind>/closed/` or `lN/work/plans/<kind>/closed/`
   - update `Status: Completed`, completion notes, and final repro/validation commands
   - future follow-up work stays as a draft plan in the correct kind, for example `tools` for test-runner/tooling work
3. Refresh docs affected by shipped behavior:
   - update relevant `Version: YYYY-MM-DD` metadata when editing reference/status docs
   - do not document draft-only future behavior as shipped
4. Run relevant validation before the commit:
   - L0 normal finalization: from `l0/`, prefer `make test-all`; for narrower safe changes use the relevant targeted
     tests from `l0/CLAUDE.md`
   - L1 normal finalization: from `l1/`, run `make test-stage1`; add `make test-stage1-trace TESTS="..."` for
     trace-sensitive paths; use `make test-stage1-trace-all` only when intentionally validating slow trace cases
   - docs-only changes still need `git diff --check`; run docs tooling when the edited docs have a generator/check
     target
5. Stage explicitly. Use `git add -u <scope>` plus explicit new files. Re-check `git status --short`.
6. Run staged whitespace check:

```bash
git diff --cached --check
```

7. Run pre-commit from the relevant level directory against the root config after staging:

```bash
uv run --group dev pre-commit run --hook-stage pre-commit -c ../.pre-commit-config.yaml --files $(git diff --cached --name-only --diff-filter=ACMR --relative)
```

If a hook reformats files, stage the hook edits, rerun `git diff --cached --check`, and rerun pre-commit before
committing.

## Commit message rules

Use a temporary message file and `git commit -F <file>` for multiline commits.

Format:

```text
Complete wide integer math follow-up.

- Extend `std.math` with `uint`, `long`, and `ulong` helper families.
- Tighten nullable integer cast and contextual literal lowering.
```

Rules:

- Summary is sentence case and ends with a period.
- A scope prefix such as `L0:` or `L1:` may be used when it improves readability, but it is not required.
- Leave exactly one blank line between summary and bullets.
- Body bullets start with `- `, are factual, sentence case, and end with a period.
- Keep each bullet on one physical line.
- Use backticks for language, command, type, module, and path identifiers.
- Do not use tag phrases such as "for clarity" or "for consistency".
- Do not add `Co-Authored-By` lines.

## Commit execution

1. Create the message file, for example:

```bash
tmp_msg=$(mktemp)
cat > "$tmp_msg" <<'EOF'
Complete wide integer math follow-up.

- Extend `std.math` with `uint`, `long`, and `ulong` helper families, add wide math runtime fixtures, and refresh L1 docs.
- Tighten nullable integer cast and contextual literal lowering, split slow nested math fixture coverage from the fast math trace target, and close the completed feature plan with a tooling follow-up for child trace support.
EOF
git commit -F "$tmp_msg"
rm -f "$tmp_msg"
```

2. If commit hooks modify files, stage the modifications and retry with the same message file content.
3. After committing, run:

```bash
git status --short
git log -1 --oneline
```

4. Final response must include:
   - commit hash and summary
   - validation commands run
   - any unstaged/untracked files intentionally left alone
