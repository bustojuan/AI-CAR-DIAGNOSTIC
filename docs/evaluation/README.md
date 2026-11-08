# Evaluation and verification

Tests establish observable software behavior, not mechanical diagnostic accuracy.
No physical vehicle repair, roadworthiness certification or clinical validation
is claimed. The release was checked on 8 November 2026 in a relocated source copy
with fresh, lockfile-based Python and npm installations.

## Release checks

| Check | Result | Scope |
| --- | --- | --- |
| Backend isolated suite | 393 passed; 41 deselected | API, safety, RAG, MCP protocol/provider doubles; excludes database and paid live tests |
| Frontend unit/component suite | 61 passed in 13 files | UI states, navigation, resolution, urgency and viewer boundaries |
| Desktop launcher | 7 passed | Service identity, environment lookup and safe startup behavior |
| TypeScript | Passed | `tsc --noEmit` |
| Production frontend build | Passed | Vite; lazy 3D bundle size warning remains |
| Ruff lint and format | Passed | Backend source, migrations and tests |

Database/browser results, publication scanning and remaining limitations are
recorded in the [release readiness report](../RELEASE_READINESS.md).
Ordinary verification does not call paid OpenAI endpoints or real merchant APIs.

## Safety scenarios

The deterministic suite covers brake/steering failure, smoke/fire, major fuel
leakage and overheating; a model cannot lower a critical rule result. It also
covers cold starting, incomplete/minor descriptions, negation, contradictory
descriptions and empty input. Structured extraction, assessment review, bounded
tool calls and invalid source-ID handling have explicit tests.

Case-resolution tests preserve original report urgency and source evidence,
aggregate the highest urgency from active cases only, keep no-active-case status
unassessed, and prevent an old resolution from hiding a newly reported critical
warning. Database tests additionally check migration, transaction rollback,
constraints, concurrent updates and persistence across fresh application instances.

## Retrieval methodology

The bundled evaluation code supports reviewed expected document/chunk anchors,
recall at four and reciprocal rank. Anchors are checked against stored source
hashes, page/section offsets and eligibility before paid evaluation. Negative
controls test whether unavailable evidence is reported honestly. Unit tests use
deterministic vectors and test candidate selection, exact identifiers,
deduplication, lexical reranking and scope/permission gates independently.

Only seven internally authored generic notes ship. Workshop and independent
question datasets preserve historical IDs/metadata, not private source texts.
Their anchors do not resolve in a fresh demo-only database. Supply authorized
sources and review anchors before evaluating a different corpus; do not treat an
unchanged historical score as a result for your own installation.

## Historical real-service evidence

The development project retains checks executed on **5 November 2026**, using
real OpenAI and PostgreSQL/pgvector. The curated
[historical summary](historical-checks.json) preserves aggregate results without
private documents, local paths, merchant records or personal consultations:

- Development retrieval set: **20 of 20** queries retrieved a reviewed anchor
  within four results; mean reciprocal rank **0.667**.
- Separate new-question set: **9 of 10**; mean reciprocal rank **0.800**.
- Two negative controls were also evaluated; these are not positive retrieval hits.
- The diagnostic validation log records **12 distinct cases** after targeted
  follow-up, with final automatic checks passing. It also records an initially
  blocked invalid-citation response and verifies 22 cited chunks against 10 local
  source files. Semantic claim grounding remains incomplete.

These are bounded development results, **not rerun for this release**, not a
benchmark for all vehicles and not a mechanical accuracy percentage. The larger
private corpus and its embeddings are excluded from publication. A source ID
and correct page establish provenance, not support for every generated claim.

## MCP and browser verification

The protocol suite exercises actual local MCP discovery/calls, input/output
schemas, timeouts, unavailable providers, result retention and the three tools.
eBay HTTP/OAuth unit tests use provider doubles; successful mocked requests do not
prove current access to Production. Search results do not establish vehicle fitment.
TecDoc has no implemented catalog adapter.

The browser suite uses real FastAPI over TCP with an explicitly injected memory
store and structured fake model. It checks diagnosis/follow-up/reload, report
views, resolution/reopening, current urgency, demo isolation, responsive layout,
3D mouse/touch controls and Engine Bay interactions. It is separate from real
PostgreSQL tests and real paid-service evaluation.

Publication screenshots are actual renders of the explicit browser demo with
synthetic reports/parts. They illustrate interaction and design, not live-service
accuracy. No video is recorded. See [capture provenance](../screenshots/README.md).

## Reproduce

Use the commands in [local setup](../setup/LOCAL_SETUP.md). Database tests require
a separate `test_...` database and direct connection. Paid retrieval/diagnostic
evaluations require your own authorized indexed corpus and explicit credentials;
inspect the CLI `--help` before opting into cost. Normal CI requires neither.
