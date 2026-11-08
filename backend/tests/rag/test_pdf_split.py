import hashlib
import json
from pathlib import Path

import pymupdf
import pytest

from app.core.config import Settings
from app.rag.extraction import extract
from app.rag.pdf_split import split_pdf


def make_pdf(path, pages):
    with pymupdf.open() as document:
        for number in range(1, pages + 1):
            document.new_page().insert_text(
                (72, 72), f"Battery reference on original page {number}."
            )
        document.set_metadata({"title": "Synthetic test manual", "author": "Project tests"})
        document.save(path)
    return path.read_bytes()


@pytest.mark.parametrize(
    "pages,counts", [(205, [100, 100, 5]), (418, [100] * 4 + [18]), (541, [100] * 5 + [41])]
)
def test_complete_ordered_split_and_original_page_numbers(tmp_path, pages, counts):
    source, destination = tmp_path / "source.pdf", tmp_path / "parts"
    original = make_pdf(source, pages)
    manifest = split_pdf(source, destination)
    assert source.read_bytes() == original
    assert manifest["source_sha256"] == hashlib.sha256(original).hexdigest()
    assert [part["pages"] for part in manifest["parts"]] == counts
    assert json.loads((destination / "manifest.json").read_text()) == manifest
    assert not manifest["ingested"] and not manifest["indexed"]
    observed = []
    for part in manifest["parts"]:
        content = (destination / part["file"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == part["sha256"]
        assert len(content) == part["bytes"] <= manifest["max_bytes_per_part"]
        with pymupdf.open(stream=content, filetype="pdf") as document:
            assert document[0].get_label() == str(part["source_page_start"])
            assert document.metadata["author"] == "Project tests"
        _, sections, warnings = extract(
            part["file"],
            "application/pdf",
            content,
            Settings(_env_file=None),
            **part["upload_form_fields"],
        )
        assert not warnings
        for section in sections:
            assert f"original page {section.page}." in section.text
        observed.extend(section.page for section in sections)
    assert observed == list(range(1, pages + 1))


def test_size_limit_causes_smaller_parts_and_single_page_failure_is_atomic(tmp_path):
    source = tmp_path / "source.pdf"
    with pymupdf.open() as document:
        for page_index in range(8):
            page = document.new_page()
            for line in range(20):
                text = hashlib.sha256(f"{page_index}:{line}".encode()).hexdigest()
                page.insert_text((72, 72 + line * 20), text, fontsize=8)
        document.save(source)
    reference = split_pdf(source, tmp_path / "reference", max_pages=1)
    limit = max(part["bytes"] for part in reference["parts"])
    manifest = split_pdf(source, tmp_path / "smaller", max_bytes=limit)
    assert len(manifest["parts"]) > 1
    assert all(part["bytes"] <= limit for part in manifest["parts"])
    assert sum(part["pages"] for part in manifest["parts"]) == 8
    destination = tmp_path / "failure"
    with pytest.raises(ValueError, match="alone exceeds"):
        split_pdf(source, destination, max_bytes=1024)
    assert not destination.exists()
    assert not list(tmp_path.glob(".pdf-split-*"))


@pytest.mark.parametrize("protection", ["password", "copy_restricted"])
def test_protected_pdfs_are_not_unlocked_or_rewritten(tmp_path, protection):
    source = tmp_path / "protected.pdf"
    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), "Protected fixture.")
        document.save(
            source,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="owner-test-password",
            user_pw="reader-test-password" if protection == "password" else "",
            permissions=pymupdf.PDF_PERM_PRINT,
        )
    original = source.read_bytes()
    destination = tmp_path / "parts"
    with pytest.raises(ValueError, match="Encrypted or copy-restricted"):
        split_pdf(source, destination)
    assert source.read_bytes() == original and not destination.exists()


def test_existing_output_is_never_replaced(tmp_path):
    source = tmp_path / "source.pdf"
    make_pdf(source, 2)
    destination = tmp_path / "parts"
    destination.mkdir()
    sentinel = destination / "keep.txt"
    sentinel.write_text("Keep this data.")
    with pytest.raises(FileExistsError):
        split_pdf(source, destination)
    assert sentinel.read_text() == "Keep this data."


def test_transient_windows_publish_lock_is_retried(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    make_pdf(source, 1)
    rename = Path.rename
    attempts = []

    def locked_once(path, target):
        attempts.append(path)
        if len(attempts) == 1:
            raise PermissionError("Temporary test file lock")
        return rename(path, target)

    monkeypatch.setattr(Path, "rename", locked_once)
    monkeypatch.setattr("app.rag.pdf_split.time.sleep", lambda _: None)
    manifest = split_pdf(source, tmp_path / "parts")
    assert len(attempts) == 2 and len(manifest["parts"]) == 1


@pytest.mark.parametrize("max_pages", [0, -1, 101, True])
def test_invalid_page_limits(tmp_path, max_pages):
    with pytest.raises(ValueError, match="between 1 and 100"):
        split_pdf(tmp_path / "unused.pdf", tmp_path / "parts", max_pages=max_pages)
