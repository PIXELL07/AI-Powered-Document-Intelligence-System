"""
Stage 1 (Section 2): document classification.

Classifies document type via keyword/structure scoring (cheap, deterministic,
no model load needed for the type decision itself), then uses the shared
spaCy NER model (lazy-loaded through model_manager) to pull out primary
parties, dates, and governing jurisdiction if present.
"""
import re
from app.pipeline.model_manager import get_model

TYPE_KEYWORDS = {
    "invoice": ["invoice", "bill to", "amount due", "invoice number", "remit payment"],
    "nda": ["non-disclosure", "nda", "confidential information", "receiving party", "disclosing party"],
    "contract": ["agreement", "party", "hereby agree", "term of this agreement", "governing law", "termination"],
    "financial_statement": ["balance sheet", "income statement", "cash flow", "fiscal year", "total assets", "net income"],
    "rfp": ["request for proposal", "rfp", "scope of work", "proposal submission", "bid deadline"],
}

JURISDICTION_PATTERN = re.compile(
    r"laws of(?: the state of| the)?\s+([A-Za-z][A-Za-z .]{1,30}?)(?=[.\n]|$)",
    re.IGNORECASE,
)


def classify_document_type(raw_text: str) -> str:
    text_lower = raw_text.lower()
    scores = {}
    for doc_type, keywords in TYPE_KEYWORDS.items():
        scores[doc_type] = sum(text_lower.count(kw) for kw in keywords)
    best_type, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score == 0:
        return "other"
    return best_type


def extract_parties_dates_jurisdiction(raw_text: str) -> dict:
    nlp = get_model("spacy_ner")
    # Cap input length fed to spaCy -- long documents don't need the whole
    # text scanned for entities in this stage, just enough to catch the
    # preamble/signature block where parties and dates typically live.
    excerpt = raw_text[:6000]
    doc = nlp(excerpt)

    orgs = []
    people = []
    dates = []
    for ent in doc.ents:
        if ent.label_ == "ORG" and ent.text not in orgs:
            orgs.append(ent.text.strip())
        elif ent.label_ == "PERSON" and ent.text not in people:
            people.append(ent.text.strip())
        elif ent.label_ in ("DATE",) and ent.text not in dates:
            dates.append(ent.text.strip())

    parties = orgs[:6] if orgs else people[:6]

    jurisdiction = None
    m = JURISDICTION_PATTERN.search(raw_text)
    if m:
        jurisdiction = m.group(1).strip().rstrip(".")

    key_dates = {}
    if dates:
        key_dates["dates_mentioned"] = dates[:10]

    return {
        "primary_parties": parties,
        "key_dates": key_dates,
        "governing_jurisdiction": jurisdiction,
    }


def run_stage1(raw_text: str) -> dict:
    doc_type = classify_document_type(raw_text)
    meta = extract_parties_dates_jurisdiction(raw_text)
    return {
        "document_type": doc_type,
        **meta,
    }
