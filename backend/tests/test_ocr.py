"""
Regression test for the OCR bug found during manual end-to-end testing:
pytesseract's word-level output was being joined with a single space,
discarding all line breaks, which caused line-anchored regexes elsewhere
in the pipeline (due date, vendor) to run past the end of their intended
line into the next one.

This tests the fix (_group_words_into_lines) directly with a synthetic
pytesseract-shaped data dict, so it doesn't depend on Tesseract being
installed or an actual image being rendered.
"""
from app.pipeline.ocr import _group_words_into_lines


def _fake_tesseract_data(lines_of_words, confidences=None):
    """Builds a dict shaped like pytesseract.image_to_data()'s output for
    a given list of lines, each a list of words."""
    text, conf, block_num, par_num, line_num = [], [], [], [], []
    for line_idx, words in enumerate(lines_of_words):
        for word in words:
            text.append(word)
            conf.append(90 if confidences is None else confidences.pop(0))
            block_num.append(1)
            par_num.append(1)
            line_num.append(line_idx)
    return {"text": text, "conf": conf, "block_num": block_num, "par_num": par_num, "line_num": line_num}


def test_words_on_same_line_join_with_space():
    data = _fake_tesseract_data([["Invoice", "Number:", "INV-3050"]])
    text, conf = _group_words_into_lines(data)
    assert text == "Invoice Number: INV-3050"


def test_words_on_different_lines_get_newline_not_space():
    data = _fake_tesseract_data([
        ["Due", "Date:", "August", "1,", "2026"],
        ["Description", "Qty", "Unit", "Price", "Amount"],
    ])
    text, conf = _group_words_into_lines(data)
    lines = text.split("\n")
    assert lines[0] == "Due Date: August 1, 2026"
    assert lines[1] == "Description Qty Unit Price Amount"
    # This is the exact bug that was found: without line grouping, a
    # "due date" regex with a bounded character class would previously
    # run straight into "Description" on the next line because there was
    # no newline to stop it.
    assert "Description" not in lines[0]


def test_empty_words_are_skipped():
    data = _fake_tesseract_data([["Hello", "", "  ", "World"]])
    text, conf = _group_words_into_lines(data)
    assert text == "Hello World"


def test_confidence_averages_only_valid_scores():
    data = _fake_tesseract_data([["Good", "Bad", "Great"]], confidences=[80, -1, 100])
    text, conf = _group_words_into_lines(data)
    assert conf == 90.0  # average of 80 and 100; -1 (Tesseract's "no confidence") excluded


def test_no_words_returns_zero_confidence():
    data = _fake_tesseract_data([])
    text, conf = _group_words_into_lines(data)
    assert text == ""
    assert conf == 0.0
