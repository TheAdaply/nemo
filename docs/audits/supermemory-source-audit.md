# Supermemory source audit ([#40](https://github.com/TheAdaply/nemo/issues/40))

**Decision: decline.** Nemo should not adapt any Supermemory code for retrieval. The public repository contains no retrieval or memory engine to adapt, and the self-hosted server that does contain one is a closed binary under a separate licence. Nemo keeps its own SQLite FTS5 baseline.

This is a read-only audit. Nothing was copied into Nemo, no dependency was added, and no Supermemory binary or hosted API was run. Every claim below was read from the repository at one pinned commit; lines marked *vendor statement* are what Supermemory's own docs in that repository say and were not independently verified.

## What was inspected

- Repository: [supermemoryai/supermemory](https://github.com/supermemoryai/supermemory), default branch `main`.
- Commit: [`8af3b910`](https://github.com/supermemoryai/supermemory/tree/8af3b9108f1a4dce45b10cfa4f8f0af027b4197b) (committed 2026-11-11). Issue #40 looked at the older `cfa6c7cb`; the conclusion is the same at both.
- Method: a shallow clone at that commit, read only. The recursive tree has 1,089 entries and was not truncated.
- Licence: [MIT](https://github.com/supermemoryai/supermemory/blob/8af3b9108f1a4dce45b10cfa4f8f0af027b4197b/LICENSE), "Copyright (c) 2025 supermemory". Using any file would require keeping that copyright and permission notice. `packages/tools`, `packages/memory-graph` and the five Python packages also declare MIT in their own manifests or `LICENSE` files.

## What the repository contains

Top-level code directories at the pinned commit, with the class the issue asks for:

| Path | Class | What it is |
|---|---|---|
| `apps/mcp` | MCP formatter/adapter | MCP server that forwards tool calls to the hosted API |
| `apps/web`, `apps/memory-graph-playground`, `apps/sdk-playground` | UI | Web app shell and demo playgrounds |
| `apps/docs` | Docs / hosted-only claims | Product documentation, including the self-hosting pages |
| `packages/tools` | SDK | Agent-framework integrations (AI SDK, OpenAI, Mastra, VoltAgent) that call the API |
| `packages/*-sdk-python`, `packages/agent-framework-python` | SDK | Python integrations that call the API |
| `packages/memory-graph`, `packages/ui`, `packages/hooks` | UI | Graph canvas and React components |
| `packages/lib`, `packages/validation` | SDK | Shared client helpers, auth, and API request/response schemas |
| `packages/docs-test` | Docs | Scripts that exercise documented API calls |

**No directory is an engine implementation.** There is no server, database schema, indexer, tokenizer, ranking function or embedding pipeline in the tree. A search of TypeScript and Python sources for `bm25`, `fts5`, `tsvector`, `pgvector`, `rerank`, `tokeniz` and `cosineSimilarity` finds only request options passed to the API (for example `rerank: true`) and the helper below.

### Candidate files

| File | Class | Finding |
|---|---|---|
| [`apps/mcp/src/server/tools/search-memory.ts`](https://github.com/supermemoryai/supermemory/blob/8af3b9108f1a4dce45b10cfa4f8f0af027b4197b/apps/mcp/src/server/tools/search-memory.ts#L40) | MCP formatter/adapter | Line 40 calls `client.search(args.query)` and formats the hits. It returns a memory ID and, when present, a document ID. It returns no line span, revision or native link. |
| [`apps/mcp/src/server/client/index.ts`](https://github.com/supermemoryai/supermemory/blob/8af3b9108f1a4dce45b10cfa4f8f0af027b4197b/apps/mcp/src/server/client/index.ts#L251-L257) | SDK | The client defaults to `https://api.supermemory.ai` (line 251) and wraps the `Supermemory` SDK. `search` (lines 308–316) is a remote call. |
| [`packages/lib/similarity.ts`](https://github.com/supermemoryai/supermemory/blob/8af3b9108f1a4dce45b10cfa4f8f0af027b4197b/packages/lib/similarity.ts#L8) | UI helper, not an engine | A 115-line helper whose core is a dot product of two embeddings passed in by the caller. It computes no embeddings and does no retrieval. |
| [`packages/validation/api.ts`](https://github.com/supermemoryai/supermemory/blob/8af3b9108f1a4dce45b10cfa4f8f0af027b4197b/packages/validation/api.ts) | SDK | Zod schemas for search requests. They describe the hosted API's parameters, not how search works. |

## The self-hosted server

The repository's own docs describe a self-hosted server, and they are explicit that its source is not here:

- *Vendor statement*, [`self-hosting/overview.mdx` line 20](https://github.com/supermemoryai/supermemory/blob/8af3b9108f1a4dce45b10cfa4f8f0af027b4197b/apps/docs/self-hosting/overview.mdx#L20): the SDKs and other components in the public repository are open source; "the downloadable self-hosted server binary is built from a separate, non-public codebase."
- *Vendor statement*, [line 65](https://github.com/supermemoryai/supermemory/blob/8af3b9108f1a4dce45b10cfa4f8f0af027b4197b/apps/docs/self-hosting/overview.mdx#L65): "The server binary is not open source", and it is free only "within its lite license limit of 10,000 stored documents".
- *Vendor statement*, [`self-hosting/local-vs-enterprise.mdx` line 8](https://github.com/supermemoryai/supermemory/blob/8af3b9108f1a4dce45b10cfa4f8f0af027b4197b/apps/docs/self-hosting/local-vs-enterprise.mdx#L8): "Its server source is not in the public repository."
- *Vendor statement*, [`self-hosting/docker.mdx` line 8](https://github.com/supermemoryai/supermemory/blob/8af3b9108f1a4dce45b10cfa4f8f0af027b4197b/apps/docs/self-hosting/docker.mdx#L8): the Docker image is prebuilt; "You don't need the server source".
- Verified: the [`server-v0.0.9` release](https://github.com/supermemoryai/supermemory/releases/tag/server-v0.0.9) (2026-10-12) ships only `install.sh`, `compose.yaml`, `manifest.json` and prebuilt `supermemory-server-*` binaries with checksums. There is no source archive for the server and no build recipe in the repository, so **there is no reproducible build**.

So the answer to "locate the self-hosted server's published source and reproducible build" is: **there is none.** The MIT licence covers the SDK, MCP and UI code. The binary has its own "lite" licence whose text is not in the repository; I did not find or read its terms.

### Does it match the cloud docs?

Per the same docs (*vendor statements*, not tested):

- **Model requirement.** [`configuration.mdx` line 8](https://github.com/supermemoryai/supermemory/blob/8af3b9108f1a4dce45b10cfa4f8f0af027b4197b/apps/docs/self-hosting/configuration.mdx#L8) says the only required input is one LLM provider key, and line 26 says to configure at least one provider. The overview says an OpenAI-compatible local endpoint such as Ollama also works. Embeddings default to a local `Xenova/bge-base-en-v1.5` model that is downloaded on first use.
- **Connector set.** [`configuration.mdx` lines 134–140](https://github.com/supermemoryai/supermemory/blob/8af3b9108f1a4dce45b10cfa4f8f0af027b4197b/apps/docs/self-hosting/configuration.mdx#L134-L140) lists connectors (Google Drive, Notion, Gmail, OneDrive) and the managed MCP server as platform-only. The self-hosted binary does not include them.

For Nemo this means the self-hosted server is not a keyless path in Nemo's sense: it needs an LLM endpoint for ingestion, a model download, and it sends telemetry unless disabled. It also has none of the connectors Nemo's roadmap needs.

## Comparison on the Nemo corpus: not run

The issue asks to compare any runnable candidate against #2/#31 on the synthetic corpus. **I did not run one, and report no numbers.**

- No candidate exists in source form, so nothing can be measured as a possible adaptation.
- The only runnable artifact is the closed binary. Measuring it would be a black-box product comparison, not a source audit: it needs an LLM endpoint, an embedding-model download, and accepting a licence I could not read. That belongs in [#32](https://github.com/TheAdaply/nemo/issues/32) as an optional local challenger, if the maintainers want it at all.
- What can be said without running it: Nemo's current hits carry a source path, an inclusive line span and a SHA-256 revision that is rechecked against the file at search time. The public MCP search tool returns a memory ID and an optional document ID. Whether the server API can return exact spans was not tested.

## Decision

1. **Decline code adaptation.** No retrieval, citation or memory-engine implementation is available under compatible source terms. `similarity.ts` is too trivial to be worth an attribution burden.
2. **No dependency.** Do not add the hosted API, the SDK or the binary as a required or default backend. All three conflict with the keyless, source-cited core in [AGENTS.md](../../AGENTS.md).
3. **Product shape only.** The memory-plus-documents result shape and the local-versus-hosted split remain useful as UX references. Per the issue, a UX pattern is not code reuse and needs no attribution.
4. **Optional follow-up, not started.** If a black-box comparison of the binary is wanted, open it under #32 with a predeclared promotion rule, the licence text reviewed first, and a local-model setup recorded.

No RED-first code issue is proposed, because nothing is being adapted.

## Limits of this audit

- One commit of one repository. Other Supermemory repositories were not audited here; the Company Brain harness is covered by [#41](https://github.com/TheAdaply/nemo/issues/41).
- The server binary was not downloaded, run, decompiled or benchmarked. Its licence text was not found.
- Statements marked *vendor statement* come from Supermemory's documentation and may be out of date or wrong.
- A keyword search can miss an engine written under unexpected names. I also read the directory listing of every top-level package and found no server code.
