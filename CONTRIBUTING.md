# Contributing

Use the isolated setup in [LOCAL_SETUP.md](docs/setup/LOCAL_SETUP.md). Run backend
unit/protocol tests, Ruff, frontend tests/build and relevant Playwright checks before
submitting changes. Update generated API types when endpoint schemas change.

Normal CI must not need paid OpenAI calls, real eBay credentials or private manuals.
Use authored fixtures and mock transports. Database tests require a separate `test_`
database; never bypass that guard. Keep new manual sources out of Git unless their
redistribution rights are documented. Preserve actual source/vehicle identities,
unknown compatibility, asset credits and critical safety priority.

Describe concrete behavior changes, relevant tests and known limits. A passing test
is not evidence of mechanical accuracy. Do not submit personal VINs, histories,
tokens, merchant snapshots or generated runtime caches.
