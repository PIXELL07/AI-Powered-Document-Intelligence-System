# Ledgerline — Document Intelligence Platform

Upload contracts, invoices, financial statements, RFPs, and NDAs in any
common format. A five-stage pipeline classifies each document, extracts
its structured content, flags anomalies, scores risk, and cross-checks it
against every other document in the same project — streaming results to
the browser stage by stage over a WebSocket, then syncing a summary
record to Notion or Airtable.

## Architecture

```
                    ┌─────────────┐        ┌──────────────┐
   Browser  ───────▶│   FastAPI   │───────▶│  Postgres /  │
  (React/Vite)       │   (web)     │        │   SQLite     │
       ▲             └──────┬──────┘        └──────────────┘
       │ WebSocket           │ enqueue
       │ (live stage         ▼
       │  updates)     ┌─────────────┐
       └───Redis───────│   Celery    │
        pub/sub         │   worker    │
                        └──────┬──────┘
                               │
                    ┌──────────┴───────────┐
                    │  5-stage pipeline     │
                    │  0 Ingestion/OCR      │
                    │  1 Classification     │
                    │  2 Extraction         │
                    │  3 Anomaly detection  │
                    │  4 Risk scoring       │
                    │  5 Contradictions*    │
                    └──────────┬───────────┘
                               ▼
                        Notion / Airtable
```
\* Stage 5 runs at the **project** level once ≥2 documents are complete,
triggered as a follow-up task after each document finishes.

**Why Celery + Redis, not just async FastAPI handlers:** the pipeline
stages are CPU-bound (OCR, NER, regex extraction over large documents),
which would block FastAPI's event loop and stall every other request/
WebSocket on the same process. Offloading to Celery workers keeps the web
process responsive purely for HTTP + WebSocket I/O.

**Why Redis pub/sub between the worker and the browser:** the Celery
worker and the FastAPI process are separate OS processes (and on Railway,
potentially separate services). The worker can't call a function on the
web process directly, so it publishes a small JSON message per stage
transition to a Redis channel (`doc:{document_id}`); the web process,
subscribed to that channel for any document with an open WebSocket,
forwards the message straight to the browser. This is what makes stage
results appear "live" rather than as a single dump at the end.

## Memory management strategy (Railway free tier constraint)

Railway's free tier gives each service roughly 512MB–1GB of RAM. OCR
(Tesseract), NER (spaCy), and document parsing (PyMuPDF/python-docx/
openpyxl) can't all sit loaded in the same process at once without
risking an OOM kill — especially with more than one document processing
concurrently.

Implemented in `backend/app/pipeline/model_manager.py`:

- **Lazy loading** — no model loads at process startup. The spaCy NER
  model loads on first actual use (Stage 1 party/date extraction), so a
  worker that never reaches that stage never pays the load cost.
- **Model cycling** — `MAX_CONCURRENT_MODELS` (default `1`) caps how many
  heavyweight models are resident at once. Requesting a new model evicts
  the current one first rather than stacking memory usage.
- **Idle unload** — a background watchdog thread unloads a model after
  `MODEL_IDLE_UNLOAD_SECONDS` (default 120s) of no use, so memory is
  reclaimed between documents without pipeline code needing to manage it
  explicitly.
- **Tesseract runs as an external OS process** (via `pytesseract`), not a
  Python-resident model — it's spawned per page and exits when done, so
  it doesn't count against the in-process model budget at all.
- **Regex/rule-based extraction over a second NER model for clause
  values** — Stage 2 deliberately uses targeted regex (payment-term days,
  liability amounts, invoice line items) instead of a second transformer
  model, since clause *values* are highly structured and a second
  resident model would blow the memory budget for marginal accuracy gain.

Net effect: steady-state memory stays bounded to "one small model +
FastAPI/Celery overhead" regardless of how many documents have been
processed in the container's lifetime.

**Storage note:** Railway's free tier filesystem is ephemeral. Uploaded
originals live only in `UPLOAD_DIR` (`/tmp` by default) long enough for
the pipeline to run; the extracted structured data — the part that
matters — is persisted to Postgres/SQLite. If a document needs
reprocessing after a container restart, it must be re-uploaded (the UI
surfaces this with a clear error rather than failing silently).

## Repo layout

```
backend/
  app/
    main.py              FastAPI app + WebSocket endpoint
    celery_app.py         Celery config
    tasks.py               Pipeline orchestration (chains all 5 stages)
    models.py, schemas.py  DB models / API schemas
    websocket_manager.py   Redis <-> WebSocket bridge
    pipeline/
      model_manager.py     Lazy-load / idle-unload model registry
      ingestion.py          Section 1: format detection + normalisation
      ocr.py                 OCR + artefact correction + confidence flag
      classification.py     Stage 1
      extraction.py           Stage 2 (branches by document type)
      anomaly_detection.py   Stage 3
      risk_scoring.py         Stage 4
      contradiction_detection.py  Stage 5
      crm_sync.py              Section 3: Notion/Airtable upsert
    routers/
      projects.py, documents.py
  requirements.txt, Dockerfile, Procfile
frontend/
  src/
    pages/     ProjectsView, ProjectDetail, DocumentProcessing, DocumentDetail
    components/ StageCard, SeverityBadge, RiskChart, ContradictionCard, CrmSyncPanel
docker-compose.yml   local dev: postgres + redis + web + worker + frontend
```

## Local development

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

- Frontend: http://localhost:5173
- API: http://localhost:8000/api/health
- The first `docker compose up` will download the spaCy `en_core_web_sm`
  model during the backend image build (a few hundred MB) — expect the
  first build to take a couple of minutes.

Without Docker:

```bash
# backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
# needs Redis + Postgres (or leave DATABASE_URL as sqlite) running locally
uvicorn app.main:app --reload &
celery -A app.celery_app.celery_app worker --loglevel=info &

# frontend
cd frontend
npm install
npm run dev
```

## Deploying to Railway

This repo deploys as **three Railway services** from the same GitHub repo:

1. **web** — `backend/`, start command from `Procfile`'s `web:` line.
   Attach Railway's Postgres and Redis plugins; Railway injects
   `DATABASE_URL` and you set `REDIS_URL` from the Redis plugin's
   connection string.
2. **worker** — same `backend/` source, override the start command to
   the `Procfile`'s `worker:` line (Railway lets you set a custom start
   command per service from the same repo/root).
3. **frontend** — `frontend/`, build with `npm run build`, serve `dist/`
   with a static file server (e.g. `npx serve -s dist -l $PORT`). Set
   `VITE_API_URL` / `VITE_WS_URL` to the deployed **web** service's public
   URL (use `wss://` for the WebSocket URL once Railway terminates TLS).

Set `NOTION_API_KEY` + `NOTION_DATABASE_ID` (or the Airtable equivalents)
as environment variables on the **web** and **worker** services — CRM
sync runs from the worker, and manual retries are triggered from the web
API.

The Notion database (or Airtable table) needs these properties/fields:
`Name` (title/text), `ContentHash` (text), `DocumentType` (select/text),
`Project` (text), `PrimaryParties` (text), `RiskScore` (number),
`CriticalAnomalies` / `WarningAnomalies` / `InfoAnomalies` (number),
`PlatformLink` (url/text).

## Authentication

Signup/login is JWT-based (`backend/app/auth.py`): bcrypt-hashed
passwords, a single long-lived access token (7 days by default) issued at
signup/login, sent as `Authorization: Bearer <token>` on every request.
Projects belong to a user (`Project.owner_id`); every project/document
route checks ownership and returns a plain 404 (not 403) for another
user's resources, so a guessed ID can't be used to confirm something
exists.

The WebSocket endpoint can't receive an `Authorization` header (browsers
don't support custom headers on the WS handshake), so the token is passed
as a query param instead: `/ws/documents/{id}?token=...`. The frontend's
`ws.js` does this automatically.

Set `JWT_SECRET` (and `SECRET_KEY`) to a real random value in production —
the defaults in `.env.example` are placeholders and must not be used as-is.

**Frontend auth**: `src/auth/AuthContext.jsx` holds the current user and
token (token in `localStorage`, fine here since this is a real deployed
app rather than an in-chat artifact sandbox). `src/auth/ProtectedRoute.jsx`
redirects to `/login` if there's no valid session. Login/Signup pages are
at `/login` and `/signup`.

This was tested end-to-end against the real running server: signup,
duplicate-email rejection, weak-password rejection, correct/incorrect
login, two separate users each only seeing their own projects, cross-user
access to another user's project/document/WebSocket correctly rejected
(404 for HTTP, WS closed with 403) rather than leaking existence, and an
authorized WebSocket connection succeeding and receiving the live status
stream.

## Testing performed

This was run end-to-end, not just written and assumed correct:

- Generated 5 real test documents spanning every required format: a
  digital PDF contract, a DOCX NDA, an XLSX invoice, a PNG scanned invoice
  (for the OCR path), and a digital PDF financial statement — several with
  deliberately planted issues (a math-mismatched total, a duplicate line
  item, a past due date, mismatched payment terms between two contracts,
  liabilities exceeding assets).
- Ran the actual stack: real Redis, a real Celery worker process, a real
  FastAPI process, real HTTP multipart uploads, and a real WebSocket
  client consuming the live stage-by-stage stream — not direct function
  calls standing in for the API.
- Every planted anomaly was correctly detected (amount mismatch, duplicate
  line item, past due date, liabilities > assets, mismatched payment
  terms), Stage 5 contradiction detection fired automatically after the
  second document in the project completed, and the CRM sync task hit the
  real Notion API, got a 403 (no credentials configured in this test
  environment), and recorded a `failed` sync status with the retry
  control intact rather than crashing the pipeline.
- One environment-specific substitution: this sandbox's network allowlist
  blocks the `en_core_web_sm` spaCy model download (Railway/Docker builds
  have unrestricted internet, so this is a sandbox limitation, not a
  product bug). Stage 1 was tested with a lightweight stand-in NER model
  so the real `classification.py` code path still executed; the shipped
  code and Dockerfile are unmodified and point at the real model.

**Three real bugs found and fixed during this pass:**
1. **OCR discarded all line structure** — `pytesseract` word output was
   being space-joined with no newlines, so line-anchored regexes (due
   date, vendor) would overshoot into the next printed line. Fixed by
   grouping words by Tesseract's line/paragraph/block indices before
   joining.
2. **XLSX header detection assumed row 0 was the header** — real invoices
   have a metadata preamble (Invoice Number, Vendor, Due Date) above the
   actual line-item table, so column matching silently failed and no line
   items were extracted. Fixed by scanning for the row that actually
   contains header-like vocabulary (`description`, `qty`, `amount`, etc.)
   rather than assuming it's first.
3. **Once the header was found correctly, trailing Tax/Total/Subtotal
   rows got misread as line items**, inflating the reconciliation sum.
   Fixed by excluding known summary-row labels from line-item parsing.

**One real limitation surfaced by testing, not yet fixed:** scanned
images/PDFs go through the OCR path, which currently produces plain text
with no table structure, so invoice line items can't be extracted for
*scanned* invoices the way they can for digital PDF/XLSX ones (total, tax,
due date, and vendor still extract fine via regex on the OCR text). Digital
PDF/DOCX/XLSX invoices are unaffected. Fixing this properly means adding
table-region detection to the OCR path (e.g. via layout analysis on word
bounding boxes) — flagged as a next step rather than silently shipped.



Set via environment variables (see `backend/.env.example`):
`MIN_TERMINATION_NOTICE_DAYS`, `MAX_PAYMENT_TERMS_DAYS`,
`YOY_CHANGE_THRESHOLD_PCT`, `OCR_CONFIDENCE_THRESHOLD`.

## Known scope boundaries / next steps

Bonus features (clause-by-clause template comparison, exportable PDF
reports, natural-language document Q&A with citations, multi-language
support) are intentionally not included in this pass so the required
Sections 1–4 pipeline is solid rather than partially stubbed. Each has a
natural extension point:
- **PDF export** — a new endpoint rendering `Document` + `Anomaly` +
  risk data through a server-side PDF library (e.g. WeasyPrint), reusing
  the same data already in `extracted_entities`/`risk_breakdown`.
- **Document QA** — a new Stage 6 task that indexes `normalized_structure`
  sections and answers questions via a small extractive-QA pass, citing
  the matched section.
- **Clause comparison** — a project-level endpoint that runs
  `extraction.extract_contract_or_nda` on two documents and diffs the
  `clauses` dicts.
- **Multi-language** — swap spaCy's `en_core_web_sm` for a language
  detected via `langdetect`, loaded through the same `model_manager`
  cycling logic so the memory budget still holds.
