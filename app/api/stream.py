"""GET /stream/{job_id} — Server-Sent Events feed of live agent activity."""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.background.events import bus

router = APIRouter(tags=["stream"])


@router.get("/stream/{job_id}")
async def stream_agent_activity(job_id: str):
    if not bus.knows(job_id):
        raise HTTPException(status_code=404, detail="Unknown job_id")

    async def event_generator():
        async for event in bus.subscribe(job_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable proxy buffering
        },
    )
