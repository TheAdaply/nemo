## Scope

Closes #
Affected [release-proof rows in issue #1](https://github.com/TheAdaply/reforge-brain/issues/1):
Unchanged/not-applicable rows:

## Independent authorship

- Test author (person/agent):
- Production-code author (different person/agent):
- Independent reviewer:

## Test-first evidence — fill in, do not just check boxes

- [ ] The test author recorded an executable RED failure for the intended missing behavior **before** production edits. Test command, failure and test commit:
- [ ] A different implementer made the same focused test GREEN without altering it. Command, result and code commit:
- [ ] The independent reviewer inspected both changes and verified the failure path and happy path.

## Required every PR

- [ ] A fresh locked install and final project-wide type/lint/test gates ran after edits settled. Exact commands and exit statuses:
- [ ] The changed behavior was exercised through the real CLI/API, not only mocks. Input and observed result:
- [ ] Relevant #1 acceptance rows and edge cases were checked; not-yet-implemented future rows were left unchecked.
- [ ] No secrets, customer content, or private Reforge events entered code, fixtures, logs or screenshots.
- [ ] Any copied code, model weights or dataset has a pinned source/version, compatible license and retained attribution.
- [ ] Documentation, CLI help and AGENTS.md still match the observed behavior. No unsupported quality, security or speed claims.

## Conditional proofs — check only when in scope

- [ ] Ranking/chunking/model change: frozen corpus and qrels; baseline vs candidate Recall@10/nDCG@10 by slice, p50/p95, index duration, RAM/disk, exact hardware and version:
- [ ] Identity/ACL change: authenticated principal source; unauthorized ID/title/count/snippet/citation and cross-tenant/revocation cases:
- [ ] Source/update/delete change: live re-index, stale-reader, repeated-update and tombstone proof:
- [ ] Citation change: source ID, revision/hash and displayed span rechecked against authoritative source:
- [ ] UI or end-user flow change: screenshot/recording and actual surface interaction proof:

## Evidence and limits

What was verified by automation:
What was exercised manually:
What was **not** checked:
Risks or rollback:
