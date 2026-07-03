"""
Section 3: CRM Sync.

Pushes a structured record to Notion or Airtable after processing.
Upserts by content_hash: if a record with the same hash already exists
in the CRM, it's updated in place rather than duplicated.
"""
import requests
from app.config import settings


def build_record_payload(document, project) -> dict:
    counts = {"critical": 0, "warning": 0, "informational": 0}
    for a in document.anomalies:
        counts[a.severity] = counts.get(a.severity, 0) + 1

    return {
        "content_hash": document.content_hash,
        "document_type": document.document_type,
        "filename": document.filename,
        "project_name": project.name,
        "primary_parties": ", ".join(document.primary_parties or []),
        "key_fields": document.extracted_entities,
        "anomaly_critical": counts.get("critical", 0),
        "anomaly_warning": counts.get("warning", 0),
        "anomaly_informational": counts.get("informational", 0),
        "risk_score": document.risk_score,
        "processed_at": document.updated_at.isoformat() if document.updated_at else None,
        "platform_link": f"/documents/{document.id}",
    }


def _find_existing_notion_page(content_hash: str) -> str | None:
    url = f"https://api.notion.com/v1/databases/{settings.NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {settings.NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    body = {"filter": {"property": "ContentHash", "rich_text": {"equals": content_hash}}}
    resp = requests.post(url, headers=headers, json=body, timeout=15)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return results[0]["id"] if results else None


def sync_to_notion(payload: dict) -> str:
    headers = {
        "Authorization": f"Bearer {settings.NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    properties = {
        "Name": {"title": [{"text": {"content": payload["filename"]}}]},
        "ContentHash": {"rich_text": [{"text": {"content": payload["content_hash"] or ""}}]},
        "DocumentType": {"select": {"name": payload["document_type"] or "other"}},
        "Project": {"rich_text": [{"text": {"content": payload["project_name"]}}]},
        "PrimaryParties": {"rich_text": [{"text": {"content": payload["primary_parties"][:1900]}}]},
        "RiskScore": {"number": payload["risk_score"] or 0},
        "CriticalAnomalies": {"number": payload["anomaly_critical"]},
        "WarningAnomalies": {"number": payload["anomaly_warning"]},
        "InfoAnomalies": {"number": payload["anomaly_informational"]},
        "PlatformLink": {"url": payload["platform_link"] if payload["platform_link"].startswith("http") else None},
    }

    existing_id = _find_existing_notion_page(payload["content_hash"]) if payload["content_hash"] else None
    if existing_id:
        url = f"https://api.notion.com/v1/pages/{existing_id}"
        resp = requests.patch(url, headers=headers, json={"properties": properties}, timeout=15)
        resp.raise_for_status()
        return existing_id
    else:
        url = "https://api.notion.com/v1/pages"
        body = {"parent": {"database_id": settings.NOTION_DATABASE_ID}, "properties": properties}
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()["id"]


def _find_existing_airtable_record(content_hash: str) -> str | None:
    url = f"https://api.airtable.com/v0/{settings.AIRTABLE_BASE_ID}/{settings.AIRTABLE_TABLE_NAME}"
    headers = {"Authorization": f"Bearer {settings.AIRTABLE_API_KEY}"}
    params = {"filterByFormula": f"{{ContentHash}}='{content_hash}'"}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    records = resp.json().get("records", [])
    return records[0]["id"] if records else None


def sync_to_airtable(payload: dict) -> str:
    url = f"https://api.airtable.com/v0/{settings.AIRTABLE_BASE_ID}/{settings.AIRTABLE_TABLE_NAME}"
    headers = {"Authorization": f"Bearer {settings.AIRTABLE_API_KEY}", "Content-Type": "application/json"}
    fields = {
        "Name": payload["filename"],
        "ContentHash": payload["content_hash"],
        "DocumentType": payload["document_type"],
        "Project": payload["project_name"],
        "PrimaryParties": payload["primary_parties"],
        "RiskScore": payload["risk_score"] or 0,
        "CriticalAnomalies": payload["anomaly_critical"],
        "WarningAnomalies": payload["anomaly_warning"],
        "InfoAnomalies": payload["anomaly_informational"],
        "PlatformLink": payload["platform_link"],
    }
    existing_id = _find_existing_airtable_record(payload["content_hash"]) if payload["content_hash"] else None
    if existing_id:
        resp = requests.patch(f"{url}/{existing_id}", headers=headers, json={"fields": fields}, timeout=15)
        resp.raise_for_status()
        return existing_id
    else:
        resp = requests.post(url, headers=headers, json={"fields": fields}, timeout=15)
        resp.raise_for_status()
        return resp.json()["id"]


def sync_document_to_crm(document, project) -> str:
    payload = build_record_payload(document, project)
    if settings.CRM_PROVIDER == "airtable":
        return sync_to_airtable(payload)
    return sync_to_notion(payload)
