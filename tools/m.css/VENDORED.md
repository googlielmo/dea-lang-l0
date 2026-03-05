## Vendored m.css Metadata

- Upstream URL: https://github.com/mosra/m.css
- Upstream commit: `0a460a7a9973a41db48f735e7b49e4da9a876325`
- Date imported: 2026-03-03
- License: MIT (SPDX: MIT) (`COPYING`)
- Imported with local modifications: yes
- See: `tools/m.css.L0-PATCHES.md`

### Local modifications and rationale

This repository vendors `m.css` for reproducible offline documentation builds.
The local patch set is documented in:

- `tools/m.css.L0-PATCHES.md`

In short, local changes adapt `documentation/doxygen.py` for the Dea/L0 docs
pipeline (compound support and robust title extraction behavior).

### Update procedure

1. Refresh `tools/m.css/` from upstream at the target commit.
2. Re-apply (or port) local changes listed in `tools/m.css.L0-PATCHES.md`.
3. Update this file with the new upstream commit and import date.
4. Regenerate docs:
   - `uv sync --group docs`
   - `./scripts/gen-docs.sh --strict`
   - optionally `./scripts/gen-docs.sh --pdf`
5. Validate expected outputs under `build/docs/`.
