"""
Shared fixtures.

Two things worth explaining:

1. Test DB isolation: each test gets a fresh SQLite file-backed DB (not
   :memory:, since Celery task code opens its own SessionLocal() and an
   in-memory SQLite DB isn't shared across connections/threads). The
   app's `get_db` dependency is overridden to use this test session
   instead of the real one.

2. Stub NER model: Stage 1's party/date extraction loads spaCy's
   `en_core_web_sm` via model_manager. Downloading that model requires
   internet access, which may not be available in a CI runner (or may
   just be slow to do on every test run). Tests instead monkeypatch
   model_manager to load a tiny local EntityRuler-based pipeline with a
   few known patterns -- enough to exercise the real code path in
   classification.py without needing the full model. This is a test-only
   substitution; production code is unaffected and still loads the real
   model.
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")  # separate DB index from dev


@pytest.fixture(autouse=True)
def flush_test_redis():
    """Rate limiting (and the WebSocket pub/sub bridge) is deliberately
    stateful in Redis across requests -- that's the point of it. But that
    means tests run back-to-back against the same Redis DB would
    otherwise accumulate rate-limit counters across unrelated tests
    (test A's signups counting against test B's limit). REDIS_URL points
    at DB index 1 in tests specifically so this flush never touches a
    real dev/prod DB (index 0)."""
    import redis as sync_redis
    from app.config import settings
    client = sync_redis.from_url(settings.REDIS_URL)
    client.flushdb()
    yield


@pytest.fixture()
def test_db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture()
def db_session(test_db_path):
    from app.database import Base

    engine = create_engine(f"sqlite:///{test_db_path}", connect_args={"check_same_thread": False})
    from app import models  # noqa: F401  -- register models on Base.metadata
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    from app.main import app
    from app.database import get_db

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def stub_ner_model_path(tmp_path):
    import spacy

    nlp = spacy.blank("en")
    ruler = nlp.add_pipe("entity_ruler")
    ruler.add_patterns([
        {"label": "ORG", "pattern": "Acme Manufacturing Inc."},
        {"label": "ORG", "pattern": "Blue Ridge Supply Co."},
        {"label": "DATE", "pattern": "January 1, 2026"},
    ])
    path = str(tmp_path / "stub_model")
    nlp.to_disk(path)
    return path


@pytest.fixture(autouse=True)
def patch_model_manager(monkeypatch, stub_ner_model_path):
    """Applied to every test automatically -- see module docstring."""
    import app.pipeline.model_manager as model_manager

    def _stub_loader(name):
        def _load():
            import spacy
            return spacy.load(stub_ner_model_path)
        return _load

    monkeypatch.setattr(model_manager, "_loader_for", _stub_loader)
    model_manager._loaded.clear()
    model_manager._last_used.clear()
    yield


@pytest.fixture()
def sample_contract_text():
    return """SUPPLY AGREEMENT

This Supply Agreement ("Agreement") is entered into as of January 1, 2026, by and between
Acme Manufacturing Inc., a Delaware corporation ("Buyer"), and Blue Ridge Supply Co.,
a North Carolina corporation ("Seller").

1. Payment Terms
Buyer shall pay all invoices within 45 days of receipt.

2. Termination
Either party may terminate this Agreement upon 10 days written notice to the other party.

3. Limitation of Liability
Seller's total liability under this Agreement shall not exceed $50,000. Buyer's total
liability shall not exceed $500,000.

4. Confidentiality
The parties agree to keep confidential information secret for a period of 3 years
following termination.

5. Governing Law
This Agreement shall be governed by and construed in accordance with the laws of
the State of Delaware.
"""


@pytest.fixture()
def make_docx(tmp_path):
    def _make(filename, paragraphs):
        import docx
        d = docx.Document()
        for text, style in paragraphs:
            p = d.add_paragraph(text)
            if style:
                p.style = d.styles[style]
        path = str(tmp_path / filename)
        d.save(path)
        return path
    return _make


@pytest.fixture()
def make_xlsx(tmp_path):
    def _make(filename, sheets):
        import openpyxl
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        for sheet_name, rows in sheets.items():
            ws = wb.create_sheet(sheet_name)
            for row in rows:
                ws.append(row)
        path = str(tmp_path / filename)
        wb.save(path)
        return path
    return _make


@pytest.fixture()
def make_pdf(tmp_path):
    def _make(filename, text):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        y = 50
        for line in text.split("\n"):
            size = 14 if line.isupper() and line.strip() else 10
            page.insert_text((50, y), line, fontsize=size, fontname="helv")
            y += 16
        path = str(tmp_path / filename)
        doc.save(path)
        doc.close()
        return path
    return _make
