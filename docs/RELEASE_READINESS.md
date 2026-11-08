# Publication readiness review

Reviewed: **8 November 2026**. This is a separate publication copy. No GitHub push,
remote overwrite, video or production deployment was performed. The development
source and personal database are preserved.

## Included structure

```text
MOTOR_GITHUB/
  README.md / LICENSE / SECURITY.md / CONTRIBUTING.md / .gitignore
  .github/workflows/          Backend and frontend checks
  backend/
    app/                     API, safety, RAG, MCP and repositories
    migrations/              Alembic revisions through 0005_resolution
    tests/                   Isolated and dedicated-database tests
    .env.example / compose.yaml / pyproject.toml / uv.lock / alembic.ini
  frontend/
    src/ / public/ / e2e/     Application, required licensed assets and browser tests
    scripts/generate-api.mjs
    package.json / package-lock.json / .env.example / build and test configuration
  docs/
    architecture/            Existing overview/detail SVG and high-resolution PNG
    screenshots/             Seven real demo captures and capture provenance
    setup/ / technical/ / evaluation/ / licenses/
    ASSET_CREDITS.md / RELEASE_READINESS.md
  scripts/                   Launcher, screenshot capture and publication audit
  Open MotorAI.vbs
```

There is no unused video directory or broken video embed. Source folders retain
their existing architecture; the README links to deeper documentation instead of
duplicating old phase prompts and progress reports.

## Copied, created and excluded

- Copied the implemented FastAPI/React source, repository interfaces, migrations,
  tests, dependency locks, configuration and required runtime assets.
- Reused the two verified architecture diagrams, including their PNG exports.
  They describe implementation, not automatic configuration of external services.
- Created an English README, local setup, RAG/MCP/safety guides, evaluation notes,
  asset credits, contribution/security policies and the user-selected MIT license.
- Preserved third-party notices and a compact historical evaluation summary.
- Excluded actual environment files, credentials, personal cases, VIN records,
  private PDFs/manual extracts, embeddings, database dumps/volumes, caches, logs,
  virtual environments, dependencies, build output, obsolete prototypes and prompts.
- Included only seven internally authored generic notes as a demo corpus. The
  private development corpus is not necessary to start the application and is not
  represented as available in a fresh installation.

Publication-only adjustments improve environment discovery in the launcher,
document ports/CORS, update stale browser selectors for the current history and
Asset Credits UI, and give the isolated viewer fixture its existing favicon.
Windows UI tests retain isolation and assertions with a 15-second per-test budget.
Test-only ports can be configured independently when another application owns
the defaults; release checks used 18104/15174 for the final targeted run.
Core diagnostic, safety, RAG, MCP and database business code is preserved. The
Compose project name is separate from the original development project's name.

## Verification

Fresh `uv sync --locked --extra dev --python 3.12` and `npm ci` succeeded in a
relocated copy outside the development folder. Windows cloud-backed hardlinks
required uv copy mode; Node was supplied as an executable tool, not as an app
dependency copied from the development environment.

| Check | Executed result |
| --- | --- |
| Backend isolated suite | **393 passed, 41 deselected** |
| Real PostgreSQL/pgvector integration | **40 passed, 394 deselected** |
| Desktop launcher tests | **7 passed** |
| Frontend unit/component tests | **61 passed in 13 files** in the final isolated run |
| TypeScript | Passed |
| Production frontend build | Passed; large lazy 3D bundle warning |
| Backend Ruff lint / format | Passed |
| Generated API contract | Matches committed TypeScript schema |
| Frontend formatting | Passed |
| Browser suite | Last complete run: **26 passed, 3 failed**; see targeted follow-up below |
| Publication screenshots | **7 real demo captures**, 1440 × 1200; visually inspected |

Database integration used a newly created dedicated test database and fresh test
schemas, not the personal application database. All five migrations ran. Tests
cover actual vector storage/search, constraints, rollback, source filtering,
conversation/report/citation persistence, resolution/reopening and concurrent
critical-warning behavior across new application instances. The temporary database
was removed afterward. A first attempt using Neon transaction pooling failed
because it rejects per-schema `search_path` startup options; the direct connection
passed. Test isolation guards were retained.

Docker is absent on the verification host, so Compose container startup was **not
executed**. Real PostgreSQL testing does not certify the local Docker installation.
The GitHub Actions service uses an isolated pgvector/PostgreSQL container, but the
workflows have not run on GitHub because this folder has not been pushed.

## Rights and security

Code and original documentation are MIT. The approved Golf VIII GLB/poster retain
CC BY 4.0 attribution. The full-compartment photo and its derived annotations retain
**CC BY-NC-SA 2.0**, including source links and visible in-app credits. The bundle
is not uniformly MIT or cleared for unrestricted commercial/marketing use.
PyMuPDF is AGPL/commercial dual licensed, and psycopg is LGPL. The MIT grant for
original files does not clear the combined backend for MIT-only redistribution.
Resolve applicable dependency obligations before claiming such clearance; no
commercial license is provided. See [dependency notices](licenses/DEPENDENCY_NOTICES.md).

The Sketchfab API successfully reconfirmed the model author and attribution
license. A fresh Flickr page check returned HTTP 502; the photograph's prior
source/license receipt is retained. This is not a fresh successful publisher-page
verification. No broader permission is inferred. Replace the photo/derived
screenshot or obtain separate authorization before commercial use. See
[asset credits](ASSET_CREDITS.md).

Publication checks inspect credential patterns, real environment files, private
locations and relative links. A separate local check compares selected files
against configured secret values without recording those values. Synthetic test
identifiers are not owner VIN records. Screenshots use only explicit demo data.
No scanner guarantees that a project is secure; this is not a penetration test or
dependency vulnerability certification.

A database credential was previously shared during development. **Rotate that
credential before publication or deployment**, even though it is excluded from
this copy. No secret is reproduced in the report and no remote credential was
changed automatically.

## Operational and product limitations

- Public multi-user deployment needs authentication, authorization, rate limits,
  secret management, backups and operational review. This release is a local MVP.
- Ordinary AI/RAG execution needs the user's OpenAI key, authorized documents and
  explicitly generated embeddings. No paid API calls were made for release checks.
- eBay adapters exist; real access, approval, quotas and availability remain
  account-dependent. eBay does not establish fitment. TecDoc needs access **and**
  implementation of its catalog adapter. Normal CI uses provider doubles.
- Historical retrieval scores describe a private corpus, not the shipped notes;
  semantic grounding and mechanical correctness are not certified.
- Golf VIII/BEW visual assets are illustrative, independent of Golf Plus/CFFB
  diagnostic configuration. Installed components are not mechanically verified.
- The lazy Three.js bundle is roughly 1.08 MB minified before gzip. Three.js emits
  a Clock deprecation warning; this is not a validated performance benchmark.

## Final verification addendum

All seven published screenshots were inspected after image decoding. The model
renders with its textures; the Engine Bay photograph and its source/license credit
are visible. Capture telemetry records zero backend API calls, browser errors or
console errors. No real model/provider output or video was captured.

The latest full browser run passed 26 cases and failed three. Focused follow-up
passed the actual hood-ray/photo-return check after broadening its screen-space
search and waiting for render frames, and passed the synthetic engine transition/
raycasting/zoom check. The final targeted report export check still fails with
`download.failure() == "canceled"`. Playwright CLI attempts canceled the blob download, whereas an independently owned
browser check successfully downloaded the real demo report and obtained its file.
The root cause has not been established. No assertion is removed or test skipped
to produce a green result. A subsequent occupied-port failure belonged to another
application; it was not stopped. Alternative test ports are now supported.

Frontend reruns also exposed a five-second UI deadline and occasional Windows
worker-startup stalls under concurrent load. Per-file isolation is preserved; the
final 61-test run passed with the Windows-only time budget adjustment. These are
software tests, not mechanical validation.

The publication pattern/link audit passes, configured secret values are absent,
and no environment/dependency/build/cache/private-document output is bundled.
The copied original source hashes and renamed diagram exports remain unchanged
in the development project. See the README/setup guide to reproduce the checks.

**Publication sign-off is conditional, not an all-green release.** Resolve the
remaining browser export check and obtain a clean full browser run before calling
CI verified. Resolve the PyMuPDF licensing path before claiming an MIT-only complete
backend, and respect the photograph's non-commercial terms. Docker startup, GitHub
Actions execution and new paid/provider live calls were not verified here. No push
or deployment was performed.
