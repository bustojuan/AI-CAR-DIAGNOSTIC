"""Prepare local PDF parts; never uploads, authorizes or indexes their contents."""

import argparse
import hashlib
import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf

from app.core.config import Settings


def publish_directory(staging, output):
    for attempt in range(5):
        if output.exists() or output.is_symlink():
            raise FileExistsError("The output directory already exists; nothing was replaced.")
        try:
            staging.rename(output)
            return
        except PermissionError:
            if attempt == 4:
                raise
            # Windows file scanners can briefly hold newly created files open.
            time.sleep(0.05 * 2**attempt)


def split_pdf(source_path, output_directory, *, max_pages=100, max_bytes=4194304):
    """Keep page order, limit part sizes and record original PDF page positions."""
    if type(max_pages) is not int or not 1 <= max_pages <= 100:
        raise ValueError("Each part must contain between 1 and 100 pages.")
    if type(max_bytes) is not int or max_bytes < 1024:
        raise ValueError("The part size limit must be at least 1024 bytes.")
    source_path = Path(source_path).resolve(strict=True)
    output = Path(output_directory).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError("Choose a new output directory; existing files are never replaced.")
    if source_path.suffix.casefold() != ".pdf":
        raise ValueError("The source must be a PDF file.")
    with source_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    with pymupdf.open(source_path) as source:
        if not source.is_pdf or not source.page_count:
            raise ValueError("The source must be a nonempty PDF.")
        if (
            source.needs_pass
            or source.is_encrypted
            or source.metadata.get("encryption")
            or not source.permissions & pymupdf.PDF_PERM_COPY
        ):
            raise ValueError("Encrypted or copy-restricted PDFs cannot be split.")
        manifest = {
            "format": "ai-car-pdf-parts-v1",
            "source_file": source_path.name,
            "source_sha256": digest,
            "source_pages": source.page_count,
            "max_pages_per_part": max_pages,
            "max_bytes_per_part": max_bytes,
            "page_numbering": "One-based physical pages in the original PDF, not printed folios.",
            "license_status": "unknown",
            "verification_status": "unverified",
            "ingested": False,
            "indexed": False,
            "parts": [],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        # Publish the directory only when every part and the manifest are complete.
        with TemporaryDirectory(prefix=".pdf-split-", dir=output.parent) as staging:
            staging = Path(staging)

            def write_range(start, end):
                with pymupdf.open() as part:
                    part.insert_pdf(source, from_page=start, to_page=end - 1)
                    part.set_metadata(
                        {
                            key: source.metadata[key]
                            for key in ("title", "author", "subject", "keywords")
                            if source.metadata.get(key)
                        }
                    )
                    part.set_page_labels(
                        [{"startpage": 0, "prefix": "", "style": "D", "firstpagenum": start + 1}]
                    )
                    content = part.tobytes(garbage=4, deflate=True, no_new_id=True)
                if len(content) > max_bytes:
                    if end - start == 1:
                        raise ValueError(
                            f"Original PDF page {start + 1} alone exceeds the part size limit. "
                            "No output was published; review source optimization or upload limits."
                        )
                    middle = (start + end) // 2
                    write_range(start, middle)
                    write_range(middle, end)
                    return
                filename = (
                    f"part-{len(manifest['parts']) + 1:03d}-pages-{start + 1:04d}-{end:04d}.pdf"
                )
                (staging / filename).write_bytes(content)
                manifest["parts"].append(
                    {
                        "file": filename,
                        "source_page_start": start + 1,
                        "source_page_end": end,
                        "pages": end - start,
                        "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "upload_form_fields": {"source_page_start": start + 1},
                    }
                )

            for start in range(0, source.page_count, max_pages):
                write_range(start, min(start + max_pages, source.page_count))
            (staging / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            publish_directory(staging, output)
    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Split a local PDF into upload-sized parts without uploading or indexing."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path, help="New private output directory")
    parser.add_argument("--pages-per-part", type=int, default=100)
    args = parser.parse_args()
    settings = Settings()
    try:
        manifest = split_pdf(
            args.source,
            args.output,
            max_pages=min(args.pages_per_part, settings.document_max_pages),
            max_bytes=settings.document_max_bytes,
        )
    except (OSError, ValueError, pymupdf.FileDataError) as error:
        parser.exit(1, f"PDF preparation failed: {error}\n")
    print(
        json.dumps(
            {
                "source_pages": manifest["source_pages"],
                "parts": len(manifest["parts"]),
                "manifest": str(args.output / "manifest.json"),
                "ingested": False,
                "indexed": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
