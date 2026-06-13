from pydantic import BaseModel, ConfigDict


class Finding(BaseModel):
    """A single detection produced by a specialist agent."""

    model_config = ConfigDict(extra="allow")

    type: str
    severity: str
    description: str
    indicators: list[str] = []
    confidence: int = 0
    timestamp_range: dict = {}


class AgentFindings(BaseModel):
    """The full output of one specialist agent for a job."""

    model_config = ConfigDict(extra="allow")

    agent_name: str
    findings: dict
    confidence_score: int | None = None
    processing_time_ms: int | None = None
