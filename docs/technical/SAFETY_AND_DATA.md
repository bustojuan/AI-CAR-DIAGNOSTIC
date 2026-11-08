# Safety and data model

The service first applies conservative phrase-based hazards to the current request
and complete user observation history. Recognized brake/steering failure, fire,
overheating and other hazards can bypass the model. Prior critical reports in the
same conversation remain critical; the LLM cannot clear them. Otherwise structured
symptom extraction, a draft and a separate model review precede backend finalization.
These finite rules are not an exhaustive natural-language safety proof.

Urgency levels are Low, Moderate, High and Critical. Unreported safety information
is unknown. Current finalization raises Low to at least Moderate when safety
information is incomplete, and then requires inspection before driving. High
requires inspection; Critical prohibits continued driving and recommends assistance.
Reports expose explanations, warning signs, missing information and driving advice,
without numerical confidence percentages. No symptoms is not an invented Low result.

PostgreSQL tables are `vehicles`, `conversations`, `messages`, `diagnostics`,
`diagnostic_hypotheses`, `technical_documents` and `document_chunks`. Alembic owns
schema changes; normal startup only validates the revision and performs idempotent
vehicle seeding. There is no automatic table recreation or user-data dump restore.

Messages, reports and normalized hypotheses are persisted in one transaction per
successful turn. Conversation row locks serialize updates, including resolution
operations. Model/validation failures commit no partial report. A local-MVP tradeoff
is holding the connection/row lock during generation. Original report urgency and
source citations are retained.

Resolution is user-reported Active/Resolved state, date and optional note on the
conversation, not independent repair verification. Reopening preserves reports;
new completed assessments reactivate a resolved case. Current vehicle urgency is
the maximum historical report urgency across **active** cases, deterministically
computed by the backend. No active cases yields null / Not assessed. Resolving
one case does not resolve unrelated cases or rewrite their safety warnings.

The frontend stores bounded conversation IDs/dates, not symptoms, VINs or full
reports, in local storage. eBay results have a stricter transient-only boundary.
Logging records sanitized categories, correlation IDs and timing, not an implemented
distributed tracing platform. General application account/permission management
is not implemented; the app is intended for local use.
