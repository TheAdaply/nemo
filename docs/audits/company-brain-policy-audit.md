# Company Brain policy audit ([#41](https://github.com/TheAdaply/nemo/issues/41))

**Decision: adapt three policy contracts as ideas, port no code.** Supermemory's Company Brain is a Slack agent harness. It is not a standalone retrieval engine and cannot run without two paid keys. Its read-scope rules, approval checkpoint and proactivity limits are worth re-specifying as Nemo issues with their own tests. Its Slack OAuth scopes, model-driven triage and admin read override should not be copied.

This is a read-only audit. Nothing was copied into Nemo, no dependency was added, and nothing from the upstream repository was run.

## What was inspected

- Repository: [supermemoryai/company-brain](https://github.com/supermemoryai/company-brain) at commit [`0071d616`](https://github.com/supermemoryai/company-brain/tree/0071d6164991ce5dccddbd645bcac631ee477572), the commit pinned in the issue.
- Licence: [Apache-2.0](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/LICENSE). There is no `NOTICE` file at the repository root. Nemo is also Apache-2.0, so a port would be compatible, but it would have to keep the copyright and licence notices and state what changed.
- Method: a shallow fetch of exactly that commit, read only. `src/` has 302 files.

How deeply each file was read:

| File | Lines | Depth |
|---|---|---|
| `src/brain/memory/read-scope.ts` | 32 | read in full |
| `src/brain/memory/search-brain.ts` | 146 | read in full |
| `src/setup/manifest.ts` | 96 | read in full |
| `src/brain/slack/public-channel-policy.ts` | 15 | read in full |
| `src/brain/memory/writeback.ts` | 219 | scope, tag and ID functions read; the rest skimmed |
| `src/brain/slack/channel-membership.ts` | 261 | membership write, reconcile comment and read query read; the rest skimmed |
| `src/brain/admin/chat.ts`, `src/brain/admin/surfaces.ts` | – | the surface-selection path only |
| `src/brain/slack/events.ts`, `turn-inbox.ts`, `triage.ts` | 358, 265, 876 | exported types, signatures and comments only |
| `src/brain/turn/approval.ts`, `src/brain/journey/guardrails.ts` | 248, 155 | exported types, constants and comments only |

Anything said below about a skimmed file describes its declared contract, not verified behavior.

## What runs without the two keys

**Nothing useful.** Verified from source, not the README:

- [`src/memory/client.ts` lines 12–17](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/src/memory/client.ts#L12-L17) throws "SUPERMEMORY_API_KEY is not set — the brain has nowhere to read or write memory" and otherwise builds a `Supermemory` SDK client with that key.
- [`src/brain/turn/brain-model.ts` line 64](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/src/brain/turn/brain-model.ts#L64) fails with "No model provider key is set" when there is no `MODEL_API_KEY`.
- The [README, lines 103–104](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/README.md#L103-L104), lists both keys as required.
- [`search-brain.ts`](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/src/brain/memory/search-brain.ts#L69-L86) does not rank anything itself. It calls `deps.searchMemoryEntries` in `hybrid` mode against a `VectorDBService`, once per container tag, then merges by similarity. I did not trace that dependency to its end, so I cannot say from this file alone where the query is executed. What is clear is that no ranking, tokenizing or indexing code lives in the file.

So this is a **harness reference, not an open standalone retrieval engine**. Pure helper functions in it (scope resolution, ID hashing, approval expiry) have no key dependency and are where its deterministic tests sit.

## Ranking of candidate contracts

Benefit is to a Nemo customer. Weight is what Nemo would have to take on. "Keyless test" means it can be specified and tested with no model or provider key.

| # | Contract | Upstream | Benefit | Weight | Keyless test | Maps to | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | Read/write scope | `read-scope.ts`, `writeback.ts` | High | Low: one pure function plus a membership table | Yes | [#13](https://github.com/TheAdaply/nemo/issues/13), [#14](https://github.com/TheAdaply/nemo/issues/14) | Adapt the rule, with the changes in the threat model below |
| 2 | Approval and resume | `turn/approval.ts` | High for any external action | Low: a state table and an expiry | Yes | [#10](https://github.com/TheAdaply/nemo/issues/10), [#29](https://github.com/TheAdaply/nemo/issues/29) | Adapt the state machine |
| 3 | Proactivity limits | `journey/guardrails.ts` | Medium: stops a bot from nagging | Low | Yes | [#19](https://github.com/TheAdaply/nemo/issues/19) | Adapt the limits, keep proactivity off |
| 4 | Update dedupe | `writeback.ts`, `slack/turn-inbox.ts` | Medium | Low | Yes | [#28](https://github.com/TheAdaply/nemo/issues/28), [#18](https://github.com/TheAdaply/nemo/issues/18) | Use as a reference only |
| 5 | Canonical tags | `writeback.ts` | Medium | Medium: tags are proposed by a model | Normalization only | [#9](https://github.com/TheAdaply/nemo/issues/9) | Defer |
| 6 | Slack routing and quiet policy | `slack/events.ts`, `slack/triage.ts` | High in Slack | High: triage is two long model prompts | Event classification only | [#19](https://github.com/TheAdaply/nemo/issues/19) | Do not adapt the triage |
| 7 | Setup UX | `setup/manifest.ts` | Medium | Low | Yes | [#24](https://github.com/TheAdaply/nemo/issues/24), [#17](https://github.com/TheAdaply/nemo/issues/17) | Idea only; do not copy the scopes |
| 8 | Native source citations | not found in the files read | – | – | – | [#7](https://github.com/TheAdaply/nemo/issues/7) | Nothing to adapt |

Notes on each:

1. **Scope.** There are three write scopes ([`writeback.ts` lines 116–126](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/src/brain/memory/writeback.ts#L116-L126)): a DM writes to the user's private tag, a private channel writes to that channel's tag, and everything else writes to one shared team tag. Reads are a superset of the write tag: shared plus the current scope, and for a DM also every private channel the asker belongs to.
2. **Approval.** Declared statuses are `pending`, `approved`, `denied`, `expired`, `executed`, `cancelled` and `error`, with a 15-minute expiry and a saved resume state ([`approval.ts` lines 12–22](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/src/brain/turn/approval.ts#L12-L22)). This matches Nemo's rule that an external action needs a preview and a human decision.
3. **Proactivity.** Off by default, at most one unprompted message per 24 hours, stop after two ignored ones, and pause for seven days after a refusal ([`guardrails.ts` lines 27–40](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/src/brain/journey/guardrails.ts#L27-L40)). A comment states that an unknown setting is "neither" consent nor a permanent opt-out.
4. **Dedupe.** A memory's ID is `company-brain-slack:{UTC date}:{sha256 of its key}` ([`writeback.ts` lines 83–92](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/src/brain/memory/writeback.ts#L83-L92)), so the same key on the same day replaces rather than duplicates. The turn inbox reserves each update as `reserved`, `duplicate` or `inactive`. Nemo's source records already key on provider-native IDs and revisions, which is stronger than a per-day hash.
5. **Tags.** Tag keys use fixed kinds (person, topic, project, customer, team, channel). The tags themselves come from model output, so only the key normalization is testable without a model.
6. **Routing.** `events.ts` has small pure predicates (ignore bot messages, detect DMs, emoji-only text). `triage.ts` decides `answer`, `ack`, `investigate` or `pass` from a model call and falls back to `pass` on a parse or provider error. Failing quiet is the right default, but the decision itself needs a model key.
7. **Setup.** Generating the Slack app manifest from the deployment's own origin is a good setup idea. See the scope warning below.
8. **Citations.** The search asks for chunks, not documents. I found no source-native link or span handling in the files read. Nemo's own source contract ([#3](https://github.com/TheAdaply/nemo/issues/3)) already goes further.

## Threat model: `resolveBrainReadContainerTags`

The function is 20 lines ([`read-scope.ts` lines 12–32](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/src/brain/memory/read-scope.ts#L12-L32)).

**The admin `override` replaces every check.** When `override` is given, the function returns it as-is ([line 19](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/src/brain/memory/read-scope.ts#L19)). There is no membership test and no intersection with what the requester may read. The only guard is in a caller: [`admin/chat.ts`](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/src/brain/admin/chat.ts) resolves requested surface IDs against the real list "rather than trusting ids from the caller". That list includes every private channel and every member's DM. So whoever can reach the admin console can read all of them. I did not find or read the route that authorizes console access, so I make no claim about who that is. For Nemo: **no parameter may replace the derived scope.** An elevated read must be a named, audited capability of an authenticated identity, and it must still be intersected with policy.

**Visibility by destination.**

| Asked in | Reads | Risk |
|---|---|---|
| Public channel | shared tag only | Low. But *everything* written from any public channel lands in one shared tag, so a public channel is treated as visible to the whole workspace. |
| Private channel | shared + that channel | Low. The answer is posted to that channel's members. |
| DM | shared + own private + every private channel the asker is in | Membership comes from a local table, not from Slack at question time. |

Reads are never wider than the place the answer is posted, which is the requester-and-audience intersection Nemo wants. Nemo should state it as a rule and test it, not rely on it falling out of the tag layout.

**Membership changes.** Membership is a local table updated from `member_joined_channel` and `member_left_channel` events, with a reconcile that re-reads the member list and removes stale rows. The upstream comment says the reconcile exists because a dropped leave event would let "a user who lost Slack access" keep reading the channel in a DM. Between a missed event and the next reconcile that access is stale. I did not read how often the reconcile runs. For Nemo: an unknown or stale membership must fail closed, and revocation needs its own test ([#11](https://github.com/TheAdaply/nemo/issues/11), [#18](https://github.com/TheAdaply/nemo/issues/18)).

**Slack Connect.** The client marks a channel external when it is externally shared, pending, or shared outside the org ([`slack/client.ts` lines 2375–2378](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/src/brain/slack/client.ts#L2375-L2378)). In the source I searched, that flag is used in one place: [`public-channel-policy.ts`](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/src/brain/slack/public-channel-policy.ts) excludes external public channels from eligibility. I found no use of it in the private-channel or DM read path. **I could not determine** whether an external member of a shared private channel, or an external user who DMs the bot, is kept away from the shared team tag. Nemo must not leave this open: an external user gets no shared-company read at all, and that needs an explicit test before any Slack answer path ships ([#19](https://github.com/TheAdaply/nemo/issues/19)).

**OAuth scopes: do not copy.** [`setup/manifest.ts` lines 29–68](https://github.com/supermemoryai/company-brain/blob/0071d6164991ce5dccddbd645bcac631ee477572/src/setup/manifest.ts#L29-L68) requests user scopes including `search:read.private`, `search:read.im`, `im:history`, `mpim:history` and `groups:history`, and bot scopes including `channels:join`, `channels:manage`, `channels:write.invites`, `files:write` and `users:read.email`. That is far broader than a read-only, consented source import. [#17](https://github.com/TheAdaply/nemo/issues/17) asks for narrow scopes; start from the minimum and justify each one.

## Tests upstream, and what Nemo should do instead

The repository has 11 `*.test.ts` files. Two are relevant: `src/brain/slack/membership-provenance.test.ts` (two cases about keeping provenance when either of two workspace mappings is revoked first) and `src/brain/slack/triage.test.ts`. They are good examples of deterministic tests over pure functions with no network.

Proposed separate Nemo issues, each RED-first with a different test author and implementer as [AGENTS.md](../../AGENTS.md) requires. None is started here.

1. **Scope rule** (under #13/#14): given a requester, a destination and a membership fixture, return the readable set. RED cases: a non-member of a private channel, a member removed after indexing, an external user, and any attempt to pass an explicit override.
2. **Approval state machine** (under #10/#29): pending to approved, denied or expired; an expired or already-decided approval cannot execute; a resumed action uses exactly the previewed input.
3. **Proactivity limits** (under #19): off by default; unknown setting sends nothing; minimum gap and ignored-streak limits hold across restarts.

If any upstream code is ever ported rather than re-specified, pin the file at commit `0071d616`, keep the Apache-2.0 notice and record the changes.

## No-go until proven

Per the issue, these stay out of Nemo until a held-out quality and safety result exists and a keyless student path works:

- Dense or graph retrieval as a default. The baseline stays lexical.
- Ambient proactivity. It stays off.
- Automatic memory writeback from conversations. Nemo's rule is reviewable, source-backed proposals.
- Any setup that needs a cloud memory key or a model key to run the required path.

## Limits of this audit

- One commit of one repository, and most of it skimmed, as the table above says.
- Nothing was run. No claim here is a measurement.
- The console's authorization, the reconcile schedule, and the Slack Connect behavior in the DM and private-channel paths were not determined.
- This does not show that the upstream product has verified enterprise authorization or deletion. Issue #41 already rules that claim out.
- The Supermemory core and SDK boundary is a separate audit, [#40](https://github.com/TheAdaply/nemo/issues/40).
