# L0 Language Server Proposal

Version: 2026-03-09

This proposal outlines a practical first LSP implementation for L0 and identifies the stdlib/runtime gaps that matter if
the server is eventually written in L0 itself.

## Summary

L0 already has enough compiler infrastructure to support a useful editor integration layer:

- Stage 1 exposes structured diagnostics in memory.
- Stage 1 analysis already computes module environments, function environments, expression types, and variable
  resolution metadata.
- The CLI and diagnostic formatter are still human-oriented rather than protocol-oriented.

The chosen path is to implement the first language server in Python, speaking JSON-RPC over stdio and shipping a
diagnostics-first MVP. This reuses the current Stage 1 compiler directly and avoids over-investing in runtime features
that are not needed for the first server.

## Why LSP and Why Stdio

The primary goal is editor integration:

- parse/type-check on open and change,
- publish diagnostics with existing L0 error codes,
- grow later into go-to-definition and hover,
- keep the transport compatible with standard editor launch flows.

The standard deployment model for LSP is a locally spawned server process connected via stdio.

## Current Repository State

### Compiler state that helps immediately

The current Stage 1 compiler in `compiler/stage1_py` already has the right internal shape for an LSP wrapper:

- `AnalysisResult.diagnostics` carries structured diagnostics with filename, module name, line, column, and span end.
- `AnalysisResult.module_envs` contains top-level symbol visibility information.
- `AnalysisResult.func_envs` contains per-function lexical scope information.
- `AnalysisResult.expr_types` and `AnalysisResult.var_ref_resolution` provide semantic facts needed for hover and
  navigation-oriented features.

This is enough to support a diagnostics MVP immediately and enough to justify a second phase around definition/hover
after targeted compiler API additions.

### Runtime and stdlib state that helps somewhat

The current L0 stdlib/runtime already provides:

- whole-file read/write via `std.io`,
- line and char reading from stdin,
- stdout/stderr printing and flushing,
- strings, vectors, maps, sets, text builders, time, environment variables, argv, and `system()`.

The runtime surface also already contains a few filesystem primitives that are not yet wrapped ergonomically at the
`std.*` layer, notably file existence and delete helpers in `sys.rt`.

### Gaps that matter

The current repository does not provide:

- JSON parsing or serialization,
- raw byte-oriented stdin/stdout APIs suitable for `Content-Length` framed LSP messages,
- path manipulation utilities,
- URI/path conversion helpers,
- directory listing or general workspace traversal,
- file metadata/stat APIs,
- file watching,
- subprocess spawning with explicit stdin/stdout/stderr pipe control.

These are the gaps that matter for an LSP hosted in L0.

## Proposed Scope

### Phase 0: Diagnostics MVP

Implement an LSP server that:

- speaks JSON-RPC 2.0 over stdio,
- supports `initialize`, `initialized`, `shutdown`, and `exit`,
- handles `textDocument/didOpen`, `textDocument/didChange`, and `textDocument/didClose`,
- runs Stage 1 analysis for the current document set,
- publishes diagnostics using existing compiler codes and source spans.

This phase should not try to solve completion, rename, references, or indexing.

### Phase 1: Definition and Hover

Add:

- `textDocument/definition`,
- `textDocument/hover`.

This requires the compiler-facing layer to expose symbol/span lookup in a structured way instead of relying on the
current CLI output paths.

### Phase 2: Richer IDE features

Possible later additions:

- completion,
- references,
- document symbols,
- workspace symbols,
- rename,
- incremental workspace indexing.

These should be treated as separate follow-on design work. They depend on parser recovery, partial-source tolerance, and
query APIs that do not exist yet.

## Implementation Options

### Option A: Python server

This is the recommended first implementation.

Pros:

- directly reuses the existing Stage 1 compiler and semantic tables,
- fastest route to a working diagnostics server,
- JSON-RPC framing and message handling are straightforward,
- low implementation risk while the editor/runtime integration surface is still separate from the self-hosted compiler,
- no need to invent a second compiler embedding boundary.

Cons:

- not implemented in L0,
- requires Python in the editor integration environment,
- may create some throwaway adapter code if the server later moves into L0.

### Option B: C server

This is viable only as a later packaging/runtime choice, not as the recommended v1.

Pros:

- easy to ship as a single native executable,
- lower runtime footprint,
- closer to the project's systems-language presentation.

Cons:

- poor reuse of the current Python compiler implementation,
- would require a new boundary to invoke or replicate Stage 1 analysis,
- significantly more protocol and memory-management code for little early product gain,
- still does not exercise L0 stdlib unless the server is written in L0 rather than merely in C.

### Option C: L0 server

This is the long-term vision but not a viable v1 path: an L0 server would require runtime and stdlib expansion (see
below) and would be a much larger project than a Python wrapper.

### Architecture Decision

Build v1 in Python.

## What L0 Is Missing For A Native L0 Server

### Essential gaps

These are the immediate missing capabilities for a serious L0-hosted LSP server:

1. JSON support.
   LSP is JSON-RPC. Without a parser and serializer, the server cannot decode requests or encode responses.
2. Byte-precise stream I/O.
   LSP framing uses headers plus exact payload byte counts. Current `read_line()` and `read_char()` are insufficient for
   efficient and correct framed message transport.
3. Path and URI utilities.
   The server needs path normalization, joining, relative/absolute handling, basename/dirname, and `file://` URI
   conversion.
4. Better filesystem APIs.
   The runtime can already answer basic existence/delete queries, but a usable tooling layer still needs wrappers plus
   directory enumeration and metadata access.

### Important but not MVP-critical gaps

- file watching,
- subprocess execution with explicit pipe capture,
- better workspace root discovery helpers,
- richer error-reporting wrappers around runtime failures.

## Compiler-Facing Changes Likely Needed Beyond Diagnostics

The diagnostics MVP can be implemented largely as a wrapper over existing analysis.

Definition and hover will likely require deliberate internal APIs such as:

- structured export of diagnostics rather than stderr-only formatting,
- source-position to AST/symbol lookup helpers,
- symbol definition location queries across locals, module-level declarations, and imports,
- hover text formatting based on resolved signatures and expression types,
- a library-style analysis entrypoint suitable for repeated editor requests.

The proposal should keep these as compiler API additions, not as CLI scraping hacks.

## Server Architecture Hypothetical Sketch

For v1:

1. A Python LSP process owns an in-memory document store keyed by URI.
2. On open/change, it writes or overlays document content for analysis.
3. It invokes Stage 1 analysis through an importable Python entrypoint rather than shelling out to `./l0c`.
4. It maps `Diagnostic` objects to LSP diagnostics, preserving source ranges and existing L0 diagnostic codes.
5. It returns structured protocol responses over stdio.

This keeps the editor server close to the canonical compiler behavior and avoids drift between CLI and tooling output.

## Acceptance Criteria For A Future Implementation

A future implementation based on this proposal should satisfy at least these scenarios:

- the server starts over stdio and completes the LSP initialize handshake,
- opening a valid file yields no diagnostics,
- opening an invalid file yields diagnostics with correct ranges and L0 codes,
- repeated edits replace old diagnostics rather than accumulating stale ones,
- cross-module diagnostics report correct file paths and module names,
- malformed JSON-RPC or malformed framing fails cleanly without hanging,
- a definition/hover milestone resolves local and imported symbols correctly once those features are added.

## Conclusion

The shortest path to a useful L0 language server is a Python implementation over stdio with diagnostics first.
