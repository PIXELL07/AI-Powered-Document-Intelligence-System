import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, SessionLocal
from app.websocket_manager import manager
from app.routers import projects, documents, auth as auth_router
from app.auth import decode_access_token
from app import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="Document Intelligence Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "*"] if settings.ENV != "production" else [settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(projects.router)
app.include_router(documents.router)


@app.on_event("startup")
async def on_startup():
    init_db()
    await manager.startup()
    logger.info("Document Intelligence Platform started (env=%s)", settings.ENV)


@app.on_event("shutdown")
async def on_shutdown():
    await manager.shutdown()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/documents/{document_id}")
async def document_ws(websocket: WebSocket, document_id: str, token: str | None = None):
    """
    Real-time pipeline progress stream (Section 2 requirement: results
    stream to the browser as each stage completes, not a single dump).

    Auth note: browsers can't attach an Authorization header to a
    WebSocket handshake, so the access token is passed as a query param
    instead (?token=...) and verified the same way as the Bearer token on
    HTTP routes. The connection is only accepted, and stage data only
    replayed, after confirming the requesting user owns the document's
    project -- otherwise a guessed document_id could be used to snoop on
    someone else's processing results.

    On connect, immediately replays any stages already completed (so a
    browser tab opened mid-processing, or refreshed, catches up instantly),
    then streams live updates published by the Celery worker via Redis.
    """
    db = SessionLocal()
    try:
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing auth token")
            return
        try:
            user_id = decode_access_token(token)
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
            return

        document = db.query(models.Document).get(document_id)
        if not document:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Document not found")
            return
        project = db.query(models.Project).get(document.project_id)
        if not project or project.owner_id != user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Not authorized for this document")
            return

        await manager.connect(document_id, websocket)
        try:
            existing = (
                db.query(models.PipelineStageResult)
                .filter_by(document_id=document_id)
                .order_by(models.PipelineStageResult.stage_number)
                .all()
            )
            for row in existing:
                await websocket.send_json({
                    "type": "stage_update",
                    "document_id": document_id,
                    "stage_number": row.stage_number,
                    "stage_name": row.stage_name,
                    "status": row.status,
                    "output": row.output if row.status == "complete" else None,
                })
            await websocket.send_json({"type": "status", "status": document.status})
        finally:
            pass

        while True:
            # Keep the connection alive; browser doesn't need to send
            # anything, but we must await recv to detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(document_id, websocket)
        db.close()
