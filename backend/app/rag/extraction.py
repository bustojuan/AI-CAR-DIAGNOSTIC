import hashlib
import re
import textwrap
import unicodedata
from html.parser import HTMLParser
from pathlib import PurePosixPath
from uuid import uuid5

import pymupdf

from app.core.exceptions import AppError
from app.rag.schemas import StoredChunk, TextSection

MIME = {
    "pdf": {"application/pdf"},
    "markdown": {"text/markdown", "text/plain"},
    "txt": {"text/plain"},
    "html": {"text/html"},
}
EXTENSIONS = {".pdf": "pdf", ".md": "markdown", ".txt": "txt", ".html": "html", ".htm": "html"}


class HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "iframe", "object", "svg", "head"}:
            self.skip += 1
        if not self.skip and tag in {"p", "div", "table", "tr", "li", "br", "h1", "h2", "h3"}:
            self.parts.append("\n\n" if tag != "tr" else "\n")
        if not self.skip and tag in {"h1", "h2", "h3"}:
            self.parts.append("#" * int(tag[-1]) + " ")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "iframe", "object", "svg", "head"}:
            self.skip = max(0, self.skip - 1)
        elif not self.skip and tag in {"p", "div", "table", "h1", "h2", "h3"}:
            self.parts.append("\n\n")
        elif not self.skip and tag in {"td", "th"}:
            self.parts.append(" | ")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def normalized(text):
    return unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n").strip()


def pdf_page_text(page):
    """Exclude fragmented curved decoration, keeping ordinary rotated technical labels.

    Some workshop PDFs draw circular copyright text one glyph at a time. MuPDF's
    layout reconstruction repeats whitespace around those fragments and interleaves
    them with procedures. Detect that pattern conservatively; never change the PDF.
    """
    blocks = page.get_text("dict", sort=True)["blocks"]

    def curved_fragment(line):
        spans = line["spans"]
        return (
            len("".join(span["text"] for span in spans).strip()) <= 4
            and all(len(span["text"].strip()) <= 1 for span in spans)
            and abs(line["dir"][1]) > 0.15
        )

    directions = {
        tuple(round(value, 2) for value in line["dir"])
        for block in blocks
        for line in block.get("lines", [])
        if curved_fragment(line)
    }
    decoration_filtered = len(directions) >= 24
    # Native block boundaries preserve paragraphs and avoid the layout renderer's
    # large runs of padding around diagram labels or merged safety instructions.
    paragraphs = []
    for block in blocks:
        lines = [
            "".join(span["text"] for span in line["spans"])
            for line in block.get("lines", [])
            if not (decoration_filtered and curved_fragment(line))
        ]
        if lines:
            paragraphs.append("\n".join(lines))
    return "\n\n".join(paragraphs), decoration_filtered


def extract(filename, content_type, content, settings, *, source_page_start=1):
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.casefold()
    kind = EXTENSIONS.get(suffix)
    if not kind or content_type.split(";", 1)[0].strip().lower() not in MIME[kind]:
        raise AppError(
            422, "unsupported_document_type", "File extension/content type is unsupported."
        )
    if (
        type(source_page_start) is not int
        or not 1 <= source_page_start <= 1000000
        or (kind != "pdf" and source_page_start != 1)
    ):
        raise AppError(
            422, "invalid_page_offset", "Original page positions apply only to PDF parts."
        )
    if not content or len(content) > settings.document_max_bytes:
        raise AppError(413, "document_size", "Document is empty or exceeds the upload limit.")
    warnings, sections = [], []
    if kind == "pdf":
        if not content.startswith(b"%PDF-"):
            raise AppError(422, "invalid_pdf", "The upload is not a valid PDF.")
        try:
            with pymupdf.open(stream=content, filetype="pdf") as document:
                if (
                    document.needs_pass
                    or not document.permissions & pymupdf.PDF_PERM_COPY
                    or document.page_count > settings.document_max_pages
                ):
                    raise AppError(
                        422, "unsupported_pdf", "Encrypted or oversized-page PDFs are unsupported."
                    )
                total = 0
                for index, page in enumerate(document):
                    text, decoration_filtered = pdf_page_text(page)
                    value = normalized(text)
                    if decoration_filtered:
                        warnings.append(
                            f"Page {index + source_page_start}: fragmented curved decoration "
                            "excluded from text extraction; source PDF unchanged."
                        )
                    total += len(value)
                    if total > settings.document_max_characters:
                        raise AppError(
                            422, "extraction_limit", "Extracted document text exceeds the limit."
                        )
                    if value:
                        sections.append(TextSection(text=value, page=index + source_page_start))
                    else:
                        warnings.append(
                            f"Page {index + source_page_start}: no text; OCR is unsupported."
                        )
        except AppError:
            raise
        except Exception:
            raise AppError(422, "invalid_pdf", "PDF extraction failed.") from None
        if not sections:
            raise AppError(422, "ocr_unsupported", "No PDF text found; OCR is not implemented.")
    else:
        try:
            value = content.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError:
            raise AppError(422, "invalid_encoding", "Text documents must use UTF-8.") from None
        if "\x00" in value or any(ord(c) < 32 and c not in "\n\r\t" for c in value):
            raise AppError(422, "binary_document", "Binary/control characters are unsupported.")
        if kind == "html":
            parser = HTMLText()
            parser.feed(value)
            value = "".join(parser.parts)
        elif kind == "txt" and re.search(r"<\s*(html|script|!doctype)", value, re.I):
            raise AppError(422, "content_type_mismatch", "HTML cannot be uploaded as plain text.")
        value = normalized(value)
        if not value or len(value) > settings.document_max_characters:
            raise AppError(422, "extraction_limit", "Document text is empty or exceeds the limit.")
        sections.append(TextSection(text=value))
    return kind, sections, warnings


def chunk_sections(document_id, sections, size, overlap):
    output = []
    for source in sections:
        heading, atoms = source.section, []
        for raw in re.split(r"\n\s*\n", source.text):
            block = raw.strip()
            if not block:
                continue
            if block.startswith("#"):
                heading = block.splitlines()[0].lstrip("# ")[:500]
            if atoms and re.fullmatch(
                r"(?i)(warning|danger|caution|advertencia|peligro)[:!]?", atoms[-1][0]
            ):
                atoms[-1][0] += "\n" + block
            else:
                atoms.append([block, heading])
        current, active_heading = "", None
        for block, heading in atoms:
            if len(block) > size and (
                "|" in block or re.search(r"(?i)warning|danger|advertencia|peligro", block)
            ):
                raise AppError(
                    422,
                    "oversized_structure",
                    "A table/warning exceeds CHUNK_SIZE; split it safely first.",
                )
            pieces = (
                textwrap.wrap(block, width=size, break_long_words=False, break_on_hyphens=False)
                if len(block) > size
                else [block]
            )
            for atom in pieces:
                if len(atom) > size:
                    raise AppError(
                        422, "oversized_structure", "Unbroken document text exceeds CHUNK_SIZE."
                    )
                changed = heading != active_heading
                if current and (changed or len(current) + len(atom) + 2 > size):
                    output.append((current, source.page, active_heading))
                    tail = current.split("\n\n")[-1]
                    current = tail if not changed and len(tail) <= overlap else ""
                    if len(current) + len(atom) + 2 > size:
                        current = ""
                active_heading = heading
                current = (current + "\n\n" + atom).strip()
        if current:
            output.append((current, source.page, active_heading))
    return [
        StoredChunk(
            chunk_id=uuid5(document_id, f"v1:{index}:{hashlib.sha256(text.encode()).hexdigest()}"),
            chunk_index=index,
            text=text,
            page=page,
            section=heading,
            content_hash=hashlib.sha256(text.encode()).hexdigest(),
        )
        for index, (text, page, heading) in enumerate(output)
    ]
