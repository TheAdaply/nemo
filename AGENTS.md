# Nemo — working agreement

Nemo never forgets. The product aim is a human-first company brain that connects consented Slack messages, meetings and docs, returns exact source-cited answers, and keeps private user context separate from approved organization memory agents can read. Self-improvement means reviewable corrections that improve held-out outcomes without weakening access or deletion; it is a future product gate, not a claim that the first retrieval slice learns. Agent traces are observations, not authority.

The first slice is an independently installable, offline retrieval engine over explicitly chosen files—not a live connector, a chat bot, reforge-app or a company-wide crawler. Start every code change from one scoped issue; [issue #1](https://github.com/TheAdaply/nemo/issues/1) is the living release-proof ledger. Before touching a file, check open issues, PRs and branches for overlap; agree on the owned files and behavior.

## Roles and gates

- **Separate people or agents:** a test author writes the executable behavior test; a different implementer writes production code; an independent reviewer checks both and runs the final gate. The implementer must not rewrite the test to make code pass. Name all three in the PR. An agent must not approve its own work.
- **RED before code:** run the focused test and show that it executes but fails for the missing behavior, not syntax, import setup or an unrelated error. Then implement the minimum needed, run that test GREEN, and refactor only while it remains green. Report exact commands and results.
- The PR template is required evidence, not decoration. Every PR links a feature issue and affected #1 rows. Run targeted tests, a fresh install and the full CI quality gates after all edits settle; do not mark a future feature as working because its issue or fixture exists.
- One change and one hypothesis per issue. State the user-visible contract, relevant failure cases, what stays out of scope and how a real caller proves it. Never ship a stub, no-op, mock-only demo, or an unsupported speed/quality claim.

## Retrieval invariants

- The canonical source record, its revision, access policy and deletion state are authoritative; any search index is derived. Each returned passage must link to its actual source ID, revision and supporting line/span. Unknown or stale access and deleted content fail closed, including titles, counts and snippets.
- A local prototype's fixture `principal`/`tenant` argument is **not authentication**. Never present synthetic ACL tests as customer-ready access control. Hosted identity must come from a trusted session/adapter before handling real private data.
- Do not ingest home directories, customer transcripts, credentials or reforge-app event payloads by default. Use explicit opt-in inputs and synthetic/public fixtures. No customer or cross-tenant claim until consent, authentication, redaction, retention and deletion are proven end to end.
- Separate retrieval relevance from answer generation. Baseline BM25 on a frozen corpus/query set; promote embeddings, rerankers or another engine only after held-out Recall@10/nDCG@10 and p50/p95 latency, index time, RAM/disk and license evidence. Never trade an ACL/citation failure for a ranking gain.
- First principles before invention: identify the consumer need, compare the simplest existing standard/stdlib/library, measure it, then add the minimum code. Do not fork Cognee, Supermemory or Onyx; adapt only a verified open-source file at a pinned commit with compatible license and required notices. No Onyx `ee/` or restricted-license code copied into this Apache-2.0 repo.
- Required development, CI and the local prototype must not need a paid coding/model API key. Use the owner's ChatGPT/Codex subscription for agent-assisted coding when available; a customer's explicitly authorized Slack/Notion/Granola credential for a future connector is a separate trust boundary and never belongs in git or tests.

## Review discipline

- Tests assert observable answers, scope, revisions, deletions, exact identifiers and citations; never source text or mock forwarding. Use fixed synthetic fixtures, pinned benchmark versions, deterministic order and explicit negative cases. Do not skip or weaken failing tests.
- Code is small, typed where useful, easy to remove and clear about trust boundaries. Keep credentials out of git and logs. Comments explain why; delete obsolete paths instead of aliases.
- Say what was run, what a real CLI user saw, and what was not verified. A green unit suite is not a customer smoke test. Reviewer must check `git diff`, license/fixture provenance and issue #1 evidence before merge.
