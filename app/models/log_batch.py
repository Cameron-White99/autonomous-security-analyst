from pydantic import BaseModel, ConfigDict, Field


class LogEntry(BaseModel):
    """A single log event. Source-specific fields (src_ip, process_name, ...) pass through."""

    model_config = ConfigDict(extra="allow")

    timestamp: str
    source: str  # "auth" | "network" | "endpoint"


class LogBatch(BaseModel):
    source: str = "demo"
    logs: list[LogEntry] = Field(min_length=1)


class IngestResponse(BaseModel):
    job_id: str
    status: str = "processing"
    message: str = "Analysis started"
