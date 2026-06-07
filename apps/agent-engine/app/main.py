"""agent-engine FastAPI service.

Endpoints:
  GET  /health
  POST /agent/run                  -> SSE stream of an agent run
  POST /agent/{thread_id}/approve  -> resume a paused run (Continue / Cancel)

Run: `uvicorn app.main:app --port 8100 --reload`
"""
from __future__ import annotations

import json
import uuid
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.config.settings import settings
from app.graph.graph_streaming import resume_and_stream, run_and_stream

app = FastAPI(title=settings.PROJECT_NAME, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class RunRequest(BaseModel):
    task: str = Field("", description="User message; may contain a URL.")
    thread_id: str | None = Field(
        None, description="Reuse to continue a conversation; omit to start fresh."
    )
    user_id: str | None = None
    site_origin: str | None = None
    history: list[HistoryTurn] = Field(
        default_factory=list, description="Prior turns for multi-turn context."
    )
    images: list[str] = Field(
        default_factory=list,
        description="Attached image data URLs (data:image/...;base64,...) for vision.",
    )


class ApproveRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    run_id: str | None = None


def _sse(ev: dict) -> dict:
    """Frame one event dict as an sse-starlette payload."""
    return {"event": ev["type"], "data": json.dumps(ev, ensure_ascii=False)}


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.post("/agent/run", tags=["agent"])
async def agent_run(req: RunRequest) -> EventSourceResponse:
    run_id = uuid.uuid4().hex
    thread_id = req.thread_id or uuid.uuid4().hex

    async def event_generator():
        async for ev in run_and_stream(
            run_id=run_id,
            thread_id=thread_id,
            task=req.task,
            user_id=req.user_id,
            site_origin=req.site_origin,
            history=[t.model_dump() for t in req.history],
            images=req.images,
        ):
            yield _sse(ev)

    return EventSourceResponse(event_generator())


@app.post("/agent/{thread_id}/approve", tags=["agent"])
async def agent_approve(thread_id: str, req: ApproveRequest) -> EventSourceResponse:
    """Resume a paused run with the user's Continue/Cancel decision and stream
    the continuation."""
    run_id = req.run_id or uuid.uuid4().hex

    async def event_generator():
        async for ev in resume_and_stream(
            run_id=run_id, thread_id=thread_id, decision=req.decision
        ):
            yield _sse(ev)

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
