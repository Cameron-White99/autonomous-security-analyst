"""POST /ingest — receive a log batch and trigger parallel analysis."""

import asyncio
import uuid

from fastapi import APIRouter

from app.background.analysis_worker import run_analysis
from app.background.events import bus
from app.models.log_batch import IngestResponse, LogBatch

router = APIRouter(tags=["ingest"])

# Keep references so running analysis tasks aren't garbage-collected
_tasks: set[asyncio.Task] = set()


@router.post("/ingest", response_model=IngestResponse, status_code=202)
async def ingest_logs(batch: LogBatch) -> IngestResponse:
    job_id = str(uuid.uuid4())
    bus.register_job(job_id)

    logs = [entry.model_dump() for entry in batch.logs]
    task = asyncio.create_task(run_analysis(job_id, logs))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)

    return IngestResponse(job_id=job_id)
