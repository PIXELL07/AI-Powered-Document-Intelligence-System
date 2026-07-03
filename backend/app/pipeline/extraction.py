"""
Stage 2 (Section 2): entity and clause extraction.

Branches by document_type (set in Stage 1). Each branch is rule/regex
based, tuned to the vocabulary of that document type -- deliberately not
relying purely on a generic NER model, since clause *values* (a 45-day
notice period, a liability cap of $2M) are highly structured and regex
extracts them far more reliably than a general-purpose NER model would.
"""
import re

MONEY_RE = r"\$\s?[\d,]+(?:\.\d{2})?|\bUSD\s?[\d,]+(?:\.\d{2})?"
DAYS_RE = r"(\d{1,4})\s*(?:calendar\s+|business\s+)?days?"


def _find_clause_window(text: str, keywords: list[str], window: int = 400) -> str | None:
    """Returns a window of text starting at the keyword match, running
    forward. Deliberately does NOT look backward from the match: clause
    headings often sit close together in real documents (a termination
    clause a line or two after a payment-terms clause), and pulling in
    preceding characters risks bleeding a neighboring clause's numbers
    (e.g. "45 days" from Payment Terms) into this clause's extraction."""
    lower = text.lower()
    for kw in keywords:
        idx = lower.find(kw)
        if idx != -1:
            return text[idx:idx + window]
    return None


def _first_number(pattern: str, text: str):
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1) if m else None


def extract_contract_or_nda(raw_text: str) -> dict:
    clauses = {}

    payment_window = _find_clause_window(raw_text, ["payment terms", "shall pay", "invoice within"])
    if payment_window:
        days = _first_number(DAYS_RE, payment_window)
        clauses["payment_terms"] = {
            "found": True,
            "days": int(days) if days else None,
            "excerpt": payment_window.strip(),
        }

    term_window = _find_clause_window(raw_text, ["termination", "terminate this agreement"])
    if term_window:
        days = _first_number(DAYS_RE, term_window)
        clauses["termination"] = {
            "found": True,
            "notice_days": int(days) if days else None,
            "excerpt": term_window.strip(),
        }

    liability_window = _find_clause_window(raw_text, ["liability", "limitation of liability", "liable"])
    if liability_window:
        amounts = re.findall(MONEY_RE, liability_window)
        clauses["liability_cap"] = {
            "found": True,
            "amounts": amounts,
            "excerpt": liability_window.strip(),
        }

    ip_window = _find_clause_window(raw_text, ["intellectual property", "work product", "assignment of ip"])
    if ip_window:
        clauses["ip_assignment"] = {"found": True, "excerpt": ip_window.strip()}

    noncompete_window = _find_clause_window(raw_text, ["non-compete", "noncompete", "restraint of trade"])
    if noncompete_window:
        clauses["non_compete"] = {"found": True, "excerpt": noncompete_window.strip()}

    conf_window = _find_clause_window(raw_text, ["confidential", "confidentiality period", "non-disclosure"])
    if conf_window:
        days = _first_number(DAYS_RE, conf_window)
        years = _first_number(r"(\d{1,2})\s*years?", conf_window)
        clauses["confidentiality"] = {
            "found": True,
            "period_days": int(days) if days else None,
            "period_years": int(years) if years else None,
            "excerpt": conf_window.strip(),
        }

    standard_clauses = ["payment_terms", "termination", "liability_cap", "confidentiality"]
    missing = [c for c in standard_clauses if c not in clauses]

    return {"clauses": clauses, "missing_standard_clauses": missing}


SUMMARY_ROW_LABELS = {"tax", "total", "subtotal", "sub-total", "shipping", "discount", "grand total"}


def extract_invoice(raw_text: str, tables: list[dict]) -> dict:
    line_items = []
    for table in tables:
        rows = table["rows"]
        if not rows:
            continue
        header = [str(c).strip().lower() for c in rows[0]]
        col_idx = {name: i for i, name in enumerate(header)}
        desc_col = next((col_idx[c] for c in col_idx if "desc" in c or "item" in c), None)
        qty_col = next((col_idx[c] for c in col_idx if "qty" in c or "quantity" in c), None)
        price_col = next((col_idx[c] for c in col_idx if "price" in c or "rate" in c or "unit" in c), None)
        amount_col = next((col_idx[c] for c in col_idx if "amount" in c or "total" in c), None)
        if desc_col is None and amount_col is None:
            continue
        for row in rows[1:]:
            if len(row) <= (desc_col or 0):
                continue
            desc_value = str(row[desc_col]).strip().lower().rstrip(":") if desc_col is not None and desc_col < len(row) else ""
            if desc_value in SUMMARY_ROW_LABELS:
                continue  # this is the invoice's own Tax/Total/Subtotal row, not a line item
            def parse_amount(v):
                if v is None:
                    return None
                v = re.sub(r"[^\d.\-]", "", str(v))
                try:
                    return float(v) if v else None
                except ValueError:
                    return None
            item = {
                "description": row[desc_col] if desc_col is not None and desc_col < len(row) else None,
                "quantity": parse_amount(row[qty_col]) if qty_col is not None and qty_col < len(row) else None,
                "unit_price": parse_amount(row[price_col]) if price_col is not None and price_col < len(row) else None,
                "amount": parse_amount(row[amount_col]) if amount_col is not None and amount_col < len(row) else None,
            }
            if item["description"] or item["amount"] is not None:
                line_items.append(item)

    total_match = re.search(r"total[:\s]*\$?\s?([\d,]+\.?\d*)", raw_text, re.IGNORECASE)
    tax_match = re.search(r"tax[:\s]*\$?\s?([\d,]+\.?\d*)", raw_text, re.IGNORECASE)
    due_date_match = re.search(r"due\s*date[:\s]*([A-Za-z0-9,/\- ]{6,25})", raw_text, re.IGNORECASE)
    vendor_match = re.search(r"(?:from|vendor|remit to)[:\s]*([A-Z][A-Za-z0-9&.,'\- ]{2,60})", raw_text, re.IGNORECASE)
    invoice_num_match = re.search(r"invoice\s*(?:#|no\.?|number)\s*[:\s]*([A-Za-z0-9\-]{3,20})", raw_text, re.IGNORECASE)

    # Explicit payment term in days, e.g. "Net 30" or "Payment terms: 45 days".
    # This is what Stage 5 needs to compare an invoice's stated term against
    # a related contract's payment_terms clause.
    payment_terms_days = None
    net_match = re.search(r"\bnet\s*(\d{1,3})\b", raw_text, re.IGNORECASE)
    if net_match:
        payment_terms_days = int(net_match.group(1))
    else:
        terms_match = re.search(r"payment\s*terms?[:\s]*(\d{1,3})\s*(?:calendar\s+|business\s+)?days?", raw_text, re.IGNORECASE)
        if terms_match:
            payment_terms_days = int(terms_match.group(1))

    def to_float(s):
        if not s:
            return None
        try:
            return float(s.replace(",", ""))
        except ValueError:
            return None

    return {
        "line_items": line_items,
        "total": to_float(total_match.group(1)) if total_match else None,
        "tax": to_float(tax_match.group(1)) if tax_match else None,
        "due_date": due_date_match.group(1).strip() if due_date_match else None,
        "vendor": vendor_match.group(1).strip() if vendor_match else None,
        "invoice_number": invoice_num_match.group(1).strip() if invoice_num_match else None,
        "payment_terms_days": payment_terms_days,
    }


FINANCIAL_METRIC_PATTERNS = {
    # [:\s|]* handles both prose ("Revenue: $50,000") and the pipe-joined
    # cell rendering our XLSX ingestion produces ("Total Revenue | 50000").
    "revenue": r"(?:total\s+)?revenue[s]?[:\s|]*\$?\s?([\d,]+\.?\d*)",
    "net_income": r"net\s+income[:\s|]*\$?\s?\(?([\d,]+\.?\d*)\)?",
    "total_assets": r"total\s+assets[:\s|]*\$?\s?([\d,]+\.?\d*)",
    "total_liabilities": r"total\s+liabilities[:\s|]*\$?\s?([\d,]+\.?\d*)",
    "operating_expenses": r"operating\s+expenses[:\s|]*\$?\s?([\d,]+\.?\d*)",
    "gross_profit": r"gross\s+profit[:\s|]*\$?\s?([\d,]+\.?\d*)",
    "cash_flow": r"(?:net\s+)?cash\s+flow[:\s|]*\$?\s?\(?([\d,]+\.?\d*)\)?",
}


def extract_financial_statement(raw_text: str, tables: list[dict]) -> dict:
    metrics = {}
    for name, pattern in FINANCIAL_METRIC_PATTERNS.items():
        m = re.search(pattern, raw_text, re.IGNORECASE)
        if m:
            try:
                metrics[name] = float(m.group(1).replace(",", ""))
            except ValueError:
                pass

    period_match = re.search(
        r"(?:fiscal\s+year|period\s+ended|for\s+the\s+year\s+ended)[:\s]*([A-Za-z0-9,\- ]{6,30})",
        raw_text, re.IGNORECASE,
    )

    return {
        "metrics": metrics,
        "reporting_period": period_match.group(1).strip() if period_match else None,
        "source_tables_count": len(tables),
    }


def run_stage2(document_type: str, raw_text: str, tables: list[dict]) -> dict:
    if document_type in ("contract", "nda", "rfp"):
        return {"type": document_type, **extract_contract_or_nda(raw_text)}
    if document_type == "invoice":
        return {"type": "invoice", **extract_invoice(raw_text, tables)}
    if document_type == "financial_statement":
        return {"type": "financial_statement", **extract_financial_statement(raw_text, tables)}
    return {"type": "other", "note": "No structured extraction rules for this document type."}
