import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, SessionLocal
from app.websocket_manager import manager
from app.routers import projects, documents
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
async def document_ws(websocket: WebSocket, document_id: str):
    """
    Real-time pipeline progress stream (Section 2 requirement: results
    stream to the browser as each stage completes, not a single dump).

    On connect, immediately replays any stages already completed (so a
    browser tab opened mid-processing, or refreshed, catches up instantly),
    then streams live updates published by the Celery worker via Redis.
    """
    await manager.connect(document_id, websocket)
    try:
        db = SessionLocal()
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
            document = db.query(models.Document).get(document_id)
            if document:
                await websocket.send_json({"type": "status", "status": document.status})
        finally:
            db.close()

        while True:
            # Keep the connection alive; browser doesn't need to send
            # anything, but we must await recv to detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(document_id, websocket)
