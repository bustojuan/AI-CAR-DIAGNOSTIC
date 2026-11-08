# Product screenshots

Captured from this publication source using `scripts/capture_screenshots.mjs`.
All screenshots use one desktop viewport, **1672 × 1060**, without browser chrome.
The visible demo mode is explicit; report and parts records are the existing
browser-only synthetic adapter's output. No live merchant responses, personal
history, credentials, network logs or private technical documents are shown.

| File | Screen |
| --- | --- |
| [01-home.png](01-home.png) | Initial Home dashboard; real approved GLB loaded. |
| [02-diagnosis.png](02-diagnosis.png) | Demo cold-start consultation in the existing workspace. |
| [03-report.png](03-report.png) | Expanded structured synthetic report; no fabricated RAG citations. |
| [04-history.png](04-history.png) | User-reported resolution workflow in demo memory. |
| [05-parts.png](05-parts.png) | Explicitly synthetic Parts candidates; no real listing retention. |
| [06-vehicle.png](06-vehicle.png) | My Vehicle and interactive Golf VIII visual. |
| [07-engine-bay.png](07-engine-bay.png) | Actual local reference photograph/markers; illustration disclosure retained. |

The Engine Bay overlay may cover the app-shell demo badge; it is captured in the
same explicit demo context and contains the photograph's own applicability and
attribution notices. Screenshots containing that photo retain **CC BY-NC-SA 2.0**
for the photographic material/derived annotations; other screenshots retain model
credits where applicable. [Full rights and sources](../ASSET_CREDITS.md).

To regenerate, install frontend dependencies and Playwright Chromium, then run
`node scripts/capture_screenshots.mjs` from the repository root. It starts and closes
its own Vite server on a free, strict test port. It neither starts a paid backend
nor calls OpenAI/eBay. No video or artificial recording is generated.
