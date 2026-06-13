from pydantic import BaseModel, ConfigDict

from app.models.finding import AgentFindings


class IncidentReport(BaseModel):
    """Correlation agent output — the synthesised incident report."""

    model_config = ConfigDict(extra="allow")

    severity: str
    title: str
    summary: str
    attack_chain: list[dict] = []
    mitre_tactics: list[str] = []
    mitre_techniques: list[str] = []
    recommended_actions: list[str] = []
    confidence: int = 0


class IncidentRecord(BaseModel):
    """A stored incident as returned by the API."""

    model_config = ConfigDict(extra="allow")

    id: str
    job_id: str
    severity: str
    title: str
    summary: str
    attack_chain: list[dict] = []
    mitre_tactics: list[str] = []
    mitre_techniques: list[str] = []
    recommended_actions: list[str] = []
    overall_confidence: int = 0
    created_at: str


class IncidentDetail(IncidentRecord):
    agent_findings: list[AgentFindings] = []
