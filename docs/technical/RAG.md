# Retrieval and technical evidence

## What is shipped

`backend/app/rag/corpus/` contains **seven internally authored generic demo notes**.
Some notes include bilingual sample content for retrieval tests; this is sample
data, not manufacturer documentation. No third-party manual, extracted manual
text, user uploads, database dump or stored embeddings are redistributed.
The source registry contains research metadata/links only, not ingestion permission.

The development database had a larger private corpus. Its reported retrieval
results do not transfer to this fresh installation; its PDF rights and exact
vehicle coverage are not independently certified. Supply your own authorized
references if you need more than generic demonstration material.

## Pipeline

1. Explicit admin API/CLI upload: PDF, Markdown, TXT or HTML, with source metadata.
2. Hash-based deduplication, bounded extraction and overlapping page/section chunks.
3. Explicit indexing of eligible processed documents with OpenAI embeddings.
4. Store text and 1536-D vectors together in PostgreSQL/pgvector.
5. Query embeddings and optional bounded English/French translations.
6. SQL cosine retrieval with permission/status/model/dimension and vehicle filters;
   optional related-Volkswagen references retain their true scope.
7. Identifier matching and deduplication, then local lexical reranking for normal
   queries (default 40 candidates, four selected, weight 0.15, similarity floor 0.35).
8. Reports cite only retrieved chunk IDs; the application constructs source metadata.

There is no ChromaDB, separate vector service, crawler, queue or implicit background
indexing. Administrator uploads are disabled without a configured `RAG_ADMIN_TOKEN`.
API/CLI ingestion does not create an object-storage archive of the original files.

## Using authorized references

Use `/api/v1/documents/upload` with metadata and `X-Admin-Token`, then explicitly
call `/api/v1/documents/{id}/index`. Use FastAPI `/docs` for the validated schema.
Set `license_status=authorized` only with permission for your intended processing;
indexing also requires `verification_status=verified`. Record the actual publisher,
model/year/engine scope, source URL permission and original page offset. Source
flags are application gates, not legal certification. Never label another vehicle's
manual as an exact match. PDF splitting can preserve original page offsets.

The CLI supports local reviewed manifests: run `python -m app.rag.cli --help`.
Keep source files, manifests with private locations and generated reports out of
the repository. The default CLI loads only the authored demo corpus; `--index`
explicitly makes paid embedding calls. Evaluation tools also require opt-in and
an indexed database; the unit tests use deterministic embeddings/providers.

## Safety and quality limits

Valid source IDs and stored page provenance do not prove per-claim grounding.
Related models do not establish installed component positions, torque values or
part fitment. Text extraction does not retain wire connectivity or all table
associations. Missing retrieval supports only “no supporting evidence was retrieved
from the available sources”, not a universal claim about all manufacturer manuals.

For evaluation, use authored queries with reviewed chunk/page anchors and negative
controls. The bundled workshop/independent evaluation JSON files contain authored
questions, IDs and metadata, not the underlying private manuals; those historical
anchors will not resolve against a fresh demo-only corpus. Supply equivalent
authorized sources and update anchors deliberately. See [evaluation](../evaluation/README.md).
