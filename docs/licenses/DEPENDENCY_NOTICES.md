# Dependency license review

The root MIT grant covers original project files. Dependencies are installed from
the lockfiles and are not vendored here. Their notices and obligations still
apply to use, packaging and distribution of the combined application. This is
not clearance to distribute the entire backend under MIT alone.

The release checked installed Python metadata and the npm lockfile. A compact
[license inventory](dependency-licenses.json) records package names, versions and
declared licenses without author emails or machine paths. Undeclared metadata
is a review gap, not evidence of permission. The inventory is not a vulnerability
scan or a determination of how licenses apply to every deployment.

| Dependency | Declared terms | Release implication |
| --- | --- | --- |
| PyMuPDF 1.28.2 / MuPDF | AGPL v3 or an Artifex commercial license | PDF extraction is implemented with this dependency. MIT on original files does not cancel applicable reciprocal/source obligations for the combined backend. No commercial license is supplied. |
| psycopg / psycopg-binary 3.3.7 | LGPL-3.0-only | Retain dependency notices and comply with LGPL requirements when bundling/distributing; no driver binary is copied here. |
| LangChain, MCP SDK, pgvector Python | MIT in the installed metadata | Retain the package copyright and permission notices. |
| React, Three.js, R3F, Drei | MIT in npm metadata | Dependencies remain separately licensed; no node_modules/build bundle is committed. |
| Lucide / applicable Feather contributions | ISC / MIT | Full notices are preserved in [LUCIDE-LICENSE.txt](LUCIDE-LICENSE.txt). |

PyMuPDF's publisher describes its [dual licensing](https://pymupdf.io/licensing)
and [AGPL/commercial availability](https://pymupdf.readthedocs.io/en/latest/about.html).
Before an MIT-only or proprietary release, resolve the PDF dependency licensing
path: comply with the applicable AGPL obligations, obtain an appropriate commercial
license, or separately authorize a dependency change. This preparation preserves
the working implementation and does not purchase a license or replace PDF parsing.

Image/model rights are separate again; see [Asset Credits](../ASSET_CREDITS.md).
