"""
Regression tests for the XLSX ingestion bug found during manual testing:
a sheet with a metadata preamble above the real line-item table was being
treated as one single table with row 0 as the header, so column matching
silently failed and produced zero line items.
"""
from app.pipeline import ingestion


def test_xlsx_header_row_detected_past_metadata_preamble(make_xlsx):
    path = make_xlsx("invoice.xlsx", {
        "Invoice": [
            ["INVOICE"],
            ["Invoice Number:", "INV-2044"],
            ["Vendor:", "Blue Ridge Supply Co."],
            ["Due Date:", "March 15, 2024"],
            ["Description", "Qty", "Unit Price", "Amount"],
            ["Widget A", 10, 25.00, 250.00],
            ["Widget B", 5, 40.00, 200.00],
        ],
    })
    result = ingestion.normalize_document(path, "invoice.xlsx")
    tables = result["tables"]
    assert len(tables) == 1
    header_row = tables[0]["rows"][0]
    # This is the regression check: the header row must be the actual
    # column-header row, not row 0 ("INVOICE", a single-cell metadata line).
    assert [str(c).lower() for c in header_row] == ["description", "qty", "unit price", "amount"]


def test_xlsx_metadata_rows_join_as_label_value_not_pipe_delimited(make_xlsx):
    """The raw_text used by downstream regex extraction needs 'Label:
    Value' rows to read naturally (no ' | ' in between), since that's
    what the due_date/vendor regexes expect."""
    path = make_xlsx("invoice.xlsx", {
        "Invoice": [
            ["Due Date:", "March 15, 2024"],
            ["Vendor:", "Blue Ridge Supply Co."],
        ],
    })
    result = ingestion.normalize_document(path, "invoice.xlsx")
    assert "Due Date: March 15, 2024" in result["raw_text"]
    assert "Vendor: Blue Ridge Supply Co." in result["raw_text"]
    assert "Due Date: |" not in result["raw_text"]


def test_xlsx_sparse_metadata_only_sheet_excluded_from_tables(make_xlsx):
    path = make_xlsx("doc.xlsx", {
        "Notes": [["Internal notes: do not send to customer"]],
    })
    result = ingestion.normalize_document(path, "doc.xlsx")
    assert result["tables"] == []
    assert "Internal notes" in result["raw_text"]


def test_docx_headings_are_preserved_as_structure(make_docx):
    path = make_docx("nda.docx", [
        ("MUTUAL NON-DISCLOSURE AGREEMENT", "Title"),
        ("This is the intro paragraph.", None),
        ("Confidentiality", "Heading 1"),
        ("The receiving party agrees to confidentiality.", None),
    ])
    result = ingestion.normalize_document(path, "nda.docx")
    headings = [s["heading"] for s in result["sections"] if s["heading"]]
    assert "MUTUAL NON-DISCLOSURE AGREEMENT" in headings
    assert "Confidentiality" in headings
    # Body text should NOT be flattened into the heading entries
    body_texts = [s["text"] for s in result["sections"] if s["text"]]
    assert any("receiving party" in t for t in body_texts)


def test_digital_pdf_extracts_text_without_ocr(make_pdf):
    path = make_pdf("contract.pdf", "SUPPLY AGREEMENT\n\nThis is a digitally authored contract.")
    result = ingestion.normalize_document(path, "contract.pdf")
    assert result["is_scanned"] is False
    assert result["ocr_confidence"] is None
    assert "digitally authored" in result["raw_text"]


def test_detect_format_rejects_unsupported_extension():
    import pytest
    with pytest.raises(ValueError):
        ingestion.detect_format("malware.exe")


def test_detect_format_recognizes_all_required_formats():
    assert ingestion.detect_format("a.pdf") == "pdf"
    assert ingestion.detect_format("a.docx") == "docx"
    assert ingestion.detect_format("a.xlsx") == "xlsx"
    assert ingestion.detect_format("a.jpg") == "image"
    assert ingestion.detect_format("a.png") == "image"
