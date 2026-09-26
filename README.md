# Nemo

**Nemo never forgets.** An open-source, source-cited company brain for people and their agents. The product goal: connect a customer's Slack, meeting notes and documents; keep personal context separate from approved company knowledge; answer questions with links to the actual evidence; and improve memory through reviewable corrections rather than unverified agent guesses.

**Status (2026-09-26): offline retrieval baseline, not a customer-ready app.** The #2 CLI indexes an explicitly selected local directory and returns ranked, source-cited passages, not generated answers. In the observed synthetic run, it indexed 3 invented files as 9 one-line passages; `ORBIT-742` ranked `projects/orbit.md` line 1 first with its exact SHA-256 revision. All 7 behavioral tests passed, including symlink-swap and failed-build retry cases. A newly built wheel also installed in a fresh Python 3.12 environment, where index, search and evaluate worked. The tiny 5-query fixture scored Recall@10 = 1.0, nDCG@10 = 1.0 and 0 false hits for unanswerable queries; these numbers establish only this synthetic baseline, not general retrieval quality or enterprise security. Live Slack/Notion/Granola connections, trusted authentication, agent collaboration and self-improvement are **NOT IMPLEMENTED**. Do not ingest customer data.

## Quickstart

From the repository root with [uv](https://docs.astral.sh/uv/) installed:

```sh
uv sync --locked --python 3.12
uv run --locked nemo index fixtures/synthetic/documents --db .nemo-demo.sqlite --json
uv run --locked nemo search 'ORBIT-742' --db .nemo-demo.sqlite --json
uv run --locked nemo evaluate fixtures/synthetic --json
uv run --locked python -m unittest discover -s tests -p 'test_*.py' -v
```

Search returns passages with source paths, line spans and SHA-256 revisions. Lower FTS5 scores rank first, with an exact-ID boost. Keep the original files accessible: search checks their current revisions before returning passages.

## The end goal

1. **Easy customer setup:** an admin installs or hosts Nemo and explicitly authorizes only selected Slack channels, Notion pages and Granola meeting notes. Sync status, lag, revocation and deletion are visible.
2. **Evidence people can trust:** a question in Nemo or Slack returns a concise answer or an honest abstention, with current, access-checked source quotes and native message/page/meeting links. Contradictions and old decisions stay traceable.
3. **Useful memory, not another document pile:** organize by project and topic; propose decisions and lessons from attributable sources; let owners approve, correct, supersede and forget them. Private conversational preferences remain private unless explicitly shared.
4. **The same context for agents:** permission-bound read-only tools let coding agents retrieve approved company knowledge. Agent work leases, handoffs and coordination live in a **separate private product**, not in Nemo's customer knowledge store.
5. **Measured adaptation:** compare correction-aware memory with a frozen no-feedback baseline on held-out company-like tasks. Reforge and its ML pipeline connect only later, with explicit consent, scoped data and reversible evaluation.

## Progress and student-sized work

- **First engine, [#2](https://github.com/TheAdaply/nemo/issues/2):** offline Python/SQLite FTS5 BM25 over an *explicitly selected* Markdown/text directory; ranked passages with source path, line span and SHA-256 revision; reproducible synthetic Recall@10/nDCG@10 scorer. The observed local CLI and fresh-wheel smoke results are summarized above; [#25](https://github.com/TheAdaply/nemo/issues/25) tracks release proof for a clean, keyless quickstart.
- **Customer-visible local demo, [#3–#11](https://github.com/TheAdaply/nemo/issues):** canonical source IDs, consented offline Slack/meeting/Notion sample imports, verified citations, extractive answers/abstention, project organization and human-reviewed decisions. These are issues, **not shipped integrations**.
- **Identity and live connectors, [#12–#24](https://github.com/TheAdaply/nemo/issues):** trusted user/tenant scopes, personal versus shared memory, actual Slack/Notion/Granola setup and synchronization, safe Slack replies. These need provider consent, real sandbox verification and source-ACL checks before customer use.
- **Quality, agent access and service, [#26–#40](https://github.com/TheAdaply/nemo/issues):** citation UI, reviewable corrections, read-only MCP, export, held-out evaluation, optional local retrieval challengers, retention, opt-in Reforge integration and enterprise operations.

Start with one bounded issue and its dependencies. The [PR template](.github/PULL_REQUEST_TEMPLATE.md) asks for separate test and production authors, a genuine executed RED assertion, GREEN, an independent review, exact smoke output and the applicable #1 rows. A fixture or unchecked issue never counts as a working feature.

## Technical and reuse choices

- The first CPU-only baseline is **Python + SQLite FTS5**. It needs no graph database, always-on service, paid model API key or agent account. Query quality is measured locally; [BEIR](https://arxiv.org/abs/2104.08663) motivates a lexical baseline but does not supply Nemo's score.
- We will **not fork** Cognee or Supermemory. Cognee's [source/derived-memory lifecycle](https://github.com/topoteretes/cognee/tree/eb90d03740755f5252b8b12cce91fd09970f2d81) informs later reviewed memory. Supermemory's [memory-plus-documents search](https://supermemory.ai/docs/recall/search) and [local-versus-hosted split](https://supermemory.ai/docs/self-hosting/overview) inform the human-facing experience. Its public repository at [the inspected revision](https://github.com/supermemoryai/supermemory/tree/cfa6c7cb17476d19ea896867406c80e8186a72ec) exposes SDK/MCP/UI code, not a verified reusable retrieval server in that tree; [#40](https://github.com/TheAdaply/nemo/issues/40) requires a pinned source/license and measured benefit before any code adaptation. Vendor comparisons are not independent proof.
- Development and required tests must stay usable without paid coding/model API keys. Customer-granted provider credentials for future live connectors are separate, secret-managed, opt-in integration requirements—not repo fixtures.

[License](LICENSE): Apache-2.0.
