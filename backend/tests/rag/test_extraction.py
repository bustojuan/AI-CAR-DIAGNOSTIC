import math
from pathlib import Path
from uuid import uuid4

import pymupdf
import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.rag.extraction import chunk_sections, extract
from app.rag.schemas import TextSection


def test_markdown_headings_and_stable_chunks():
    identifier = uuid4()
    sections = [
        TextSection(
            text="# Starting\n\nBattery check.\n\n# Cooling\n\nCooling information.", page=2
        )
    ]
    chunks = chunk_sections(identifier, sections, 300, 20)
    assert [c.section for c in chunks] == ["Starting", "Cooling"]
    assert all(c.page == 2 for c in chunks)
    assert chunks == chunk_sections(identifier, sections, 300, 20)


def test_html_scripts_never_become_context():
    content = (
        b"<html><head><script>secret()</script></head><body><h1>Cooling</h1>"
        b"<p>Cool engine.</p><iframe>bad</iframe></body></html>"
    )
    kind, sections, _ = extract("x.html", "text/html", content, Settings(_env_file=None))
    assert kind == "html" and "Cooling" in sections[0].text
    assert "secret" not in sections[0].text and "bad" not in sections[0].text


def test_pdf_page_provenance_and_scanned_pdf_rejected():
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "Battery and starter test.")
    document.new_page().insert_text((72, 72), "Cooling test.")
    _, sections, _ = extract(
        "x.pdf", "application/pdf", document.tobytes(), Settings(_env_file=None)
    )
    assert [s.page for s in sections] == [1, 2]
    document.close()
    empty = pymupdf.open()
    empty.new_page()
    with pytest.raises(AppError) as failure:
        extract("x.pdf", "application/pdf", empty.tobytes(), Settings(_env_file=None))
    assert failure.value.code == "ocr_unsupported"
    empty.close()


@pytest.mark.parametrize(
    "filename,mime,content",
    [
        ("x.exe", "text/plain", b"data"),
        ("x.pdf", "text/plain", b"%PDF-test"),
        ("x.pdf", "application/pdf", b"not PDF"),
        ("x.txt", "text/plain", b"\xff\xfe"),
        ("x.txt", "text/plain", b"abc\x00"),
        ("x.txt", "text/plain", b"<html>body</html>"),
        ("x.txt", "text/plain", b"  "),
    ],
)
def test_invalid_documents(filename, mime, content):
    with pytest.raises(AppError):
        extract(filename, mime, content, Settings(_env_file=None))


def test_oversized_upload_and_warning_preservation():
    with pytest.raises(AppError):
        extract(
            "x.txt", "text/plain", b"x" * 2048, Settings(_env_file=None, document_max_bytes=1024)
        )
    sections = [TextSection(text="WARNING\n\n" + "Hot cooling system. " * 30)]
    with pytest.raises(AppError) as failure:
        chunk_sections(uuid4(), sections, 300, 0)
    assert failure.value.code == "oversized_structure"


def test_demo_corpus_extracts_and_chunks_within_bound():
    corpus = Path(__file__).resolve().parents[2] / "app/rag/corpus"
    count = 0
    for path in corpus.glob("*.md"):
        _, sections, _ = extract(
            path.name, "text/markdown", path.read_bytes(), Settings(_env_file=None)
        )
        chunks = chunk_sections(uuid4(), sections, 1200, 150)
        assert chunks and all(len(c.text) <= 1200 for c in chunks)
        count += 1
    assert count == 7


def test_original_page_offsets_cover_empty_page_warnings_and_reject_non_pdf():
    settings = Settings(_env_file=None)
    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), "Original page 101 text.")
        document.new_page()
        _, sections, warnings = extract(
            "part.pdf", "application/pdf", document.tobytes(), settings, source_page_start=101
        )
    assert sections[0].page == 101 and warnings == ["Page 102: no text; OCR is unsupported."]
    with pytest.raises(AppError) as failure:
        extract("x.md", "text/markdown", b"Battery.", settings, source_page_start=101)
    assert failure.value.code == "invalid_page_offset"


def test_curved_glyph_decoration_does_not_corrupt_workshop_text():
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Gearbox identification and clutch allocation.")
        page.insert_text((100, 350), "Vertical technical label", rotate=90)
        for angle in range(0, 360, 6):
            radians = math.radians(angle)
            point = pymupdf.Point(300 + 120 * math.cos(radians), 400 + 120 * math.sin(radians))
            page.insert_text(point, "W", fontsize=8, morph=(point, pymupdf.Matrix(angle)))
        _, sections, warnings = extract(
            "workshop.pdf", "application/pdf", document.tobytes(), Settings(_env_file=None)
        )
    assert "Gearbox identification and clutch allocation." in sections[0].text
    assert "Vertical technical label" in sections[0].text
    assert sections[0].text.count("W") < 10
    assert len(warnings) == 1 and "source PDF unchanged" in warnings[0]


def test_ordinary_rotated_diagram_labels_are_preserved():
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Battery checks.")
        page.insert_text((100, 350), "Vertical fuse reference", rotate=90)
        _, sections, warnings = extract(
            "diagram.pdf", "application/pdf", document.tobytes(), Settings(_env_file=None)
        )
    assert all(word in sections[0].text for word in ("Vertical", "fuse", "reference"))
    assert not warnings


def test_pdf_native_paragraphs_and_sparse_diagram_labels_fit_extraction_limits():
    with pymupdf.open() as document:
        page = document.new_page(width=1200, height=1600)
        for index, text in enumerate(
            [
                "Safety precautions. " + "Observe the complete procedure. " * 14,
                "Handling components incorrectly is dangerous. "
                + "Keep this paragraph intact. " * 14,
                "Storage instructions. " + "Retain the source context. " * 14,
            ]
        ):
            page.insert_textbox(pymupdf.Rect(70, 70 + index * 200, 450, 250 + index * 200), text)
        page.insert_text((1050, 1400), "J234")
        _, sections, _ = extract(
            "workshop.pdf",
            "application/pdf",
            document.tobytes(),
            Settings(_env_file=None, document_max_characters=3000),
        )
    chunks = chunk_sections(uuid4(), sections, 1200, 150)
    assert all(len(chunk.text) <= 1200 for chunk in chunks)
    assert "J234" in sections[0].text and "dangerous" in sections[0].text
    assert " ".join(sections[0].text.split()).count("Retain the source context.") == 14
