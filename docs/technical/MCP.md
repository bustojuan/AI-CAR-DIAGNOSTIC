# Automotive MCP and providers

One FastMCP server exposes three structured read-only tools:

| Tool | Purpose | Current limitations |
| --- | --- | --- |
| `search_parts` | Candidate search by component/reference and vehicle context | Candidates are not replacement recommendations or fitment proof. |
| `check_compatibility` | Provider-supported vehicle-to-part application lookup | eBay currently returns unknown; demo is synthetic. |
| `get_part_prices` | Identified listing/part quote lookup | Currency/quantity/tax/stock limits remain explicit. |

FastAPI Parts routes call an MCP gateway with exact tool discovery/schema checks,
bounded requests/results, request IDs and sanitized telemetry. The server delegates
to a selected provider adapter and normalizes its response. These are one server's
three tools, not three independent MCP servers. **MCP Parts operations do not need OpenAI.**

## Providers

| Selection | Implemented | Credentials / meaning |
| --- | --- | --- |
| `unavailable` | Yes; safe default | No external service; no invented results. |
| `demo` | Yes | Authored synthetic examples, explicitly labeled. |
| `ebay` | Yes | Production `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET`, App ID and Cert ID; read-only OAuth application token + Browse. |
| `ebay_sandbox` | Yes | Separate Sandbox pair; test listings never labeled real offers. |
| TecDoc | **No adapter** | Only a local onboarding checker exists; authorized access/contract and implementation are pending. |

eBay returns listing candidates, prices, links and availability only where supplied.
It does not implement real fitment matching, user account access, purchases or checkout.
Credentials must come from one enabled keyset in the selected environment. A working
adapter is not a guarantee of current provider approval, quotas or availability.

eBay/Sandbox results live only in transient Parts UI state, with no-store responses
and clearing on page navigation/visibility changes. They are excluded from saved
diagnoses, model assessment context and application-controlled persistent browser
storage. Repository guards reject reports containing those results. Do not paste
listing data into report notes/uploads; independent browsers/proxies/merchant sites
are outside this application's retention boundary.

The diagnostic tool workflow is separate and bounded for non-transient providers,
after safety triage; critical diagnoses skip catalog calls. Active eBay providers
are intentionally bypassed by that persistent-report workflow. A future combined
catalog/merchant configuration would require deliberate routing changes; the current
factory selects one provider at a time.

## Transports

Stdio is recommended locally: configure `MCP_ENABLED=true`, `MCP_TRANSPORT=stdio`
and a provider, then start the ordinary backend. It launches bounded child sessions;
only the necessary selected-provider configuration is forwarded, not database or
OpenAI credentials.

Authenticated loopback Streamable HTTP is implemented as an alternative:

```bash
cd backend
# Configure MCP_TOKEN (>=24 random characters), MCP_TRANSPORT=http and provider.
uv run --locked python -m app.mcp.server --transport http
```

The backend uses matching `MCP_HTTP_URL=http://127.0.0.1:8766/mcp` and `MCP_TOKEN`.
Never publish that listener as an unauthenticated public service. Local tool schema,
timeouts, invalid responses, retention and provider transports are tested with
synthetic fixtures; normal CI requires no merchant credentials.
