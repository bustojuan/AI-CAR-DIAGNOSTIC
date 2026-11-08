# Security

Motor is a local educational/portfolio MVP, not a public multi-user service.
Do not expose it to the internet without general authentication, authorization,
rate limits, deployment controls and an operational security review.

- Keep `.env`, provider keys, admin tokens, uploads, manual text, embeddings and
  diagnostic histories outside Git. Use credential-free `.env.example` templates.
- Never place OpenAI, MCP or eBay secrets in Vite variables or screenshots.
- RAG admin tokens and optional HTTP MCP tokens are separate from application login.
- Rotate credentials that were ever shared in chat, screenshots or another public
  location. Removing a value from this copy does not invalidate an exposed secret.
- eBay offers are transient; do not paste them into saved reports/notes/uploads.
- The app masks common provider errors/log details, but no finite scanner, prompt
  rule or UI validation is a complete security guarantee.

For a vulnerability, contact the repository maintainer privately through the
repository hosting platform. Do not open a public issue containing secrets,
personal diagnostic data or a working exploit against someone else's deployment.
The publication audit and remaining release checks are documented in
[the readiness report](docs/RELEASE_READINESS.md).
