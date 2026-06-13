"""GET /incidents — list and retrieve incident reports."""

from fastapi import APIRouter, HTTPException

from app.db.repositories import findings as findings_repo
from app.db.repositories import incidents as incidents_repo
from app.models.incident import IncidentDetail, IncidentRecord

router = APIRouter(tags=["incidents"])


@router.get("/incidents", response_model=list[IncidentRecord])
async def list_incidents(limit: int = 50):
    return await incidents_repo.list_incidents(limit=limit)


@router.get("/incidents/{incident_id}", response_model=IncidentDetail)
async def get_incident(incident_id: str):
    incident = await incidents_repo.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    findings = await findings_repo.get_findings_for_incident(incident_id)
    return {**incident, "agent_findings": findings}
