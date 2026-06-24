from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.agent_registry import get_agent_detail, get_all_agents, route_by_concepts
from app.core.database import get_db
from app.core.security import Role, require_admin, require_readonly
from app.models.agent_model import AgentCatalog
from app.schemas.agent import (
    AgentCreateRequest,
    AgentDetailResponse,
    AgentResponse,
    AgentRouteRequest,
    AgentRouteResponse,
    AgentUpdateRequest,
)

router = APIRouter(prefix="/api/v1/agents", tags=["agent"])


@router.post("/route", response_model=AgentRouteResponse)
def route_agents(
    body: AgentRouteRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_readonly),
):
    return route_by_concepts(db, body.concept_ids)


@router.get("", response_model=list[AgentResponse])
def list_agents(
    db: Session = Depends(get_db),
    _role: Role = Depends(require_readonly),
):
    return get_all_agents(db)


@router.get("/catalog", response_model=list[AgentResponse])
def list_agent_catalog(
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    return db.query(AgentCatalog).order_by(AgentCatalog.id.asc()).all()


@router.post("/catalog", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent_catalog(
    body: AgentCreateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    existing = db.query(AgentCatalog).filter(AgentCatalog.agent_id == body.agent_id).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="agent already exists")

    agent = AgentCatalog(
        agent_id=body.agent_id,
        name=body.name,
        agent_type=body.agent_type,
        description=body.description,
        capabilities=body.capabilities,
        is_active=body.is_active,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.put("/catalog/{agent_id}", response_model=AgentResponse)
def update_agent_catalog(
    agent_id: str,
    body: AgentUpdateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    agent = db.query(AgentCatalog).filter(AgentCatalog.agent_id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")

    agent.name = body.name
    agent.agent_type = body.agent_type
    agent.description = body.description
    agent.capabilities = body.capabilities
    agent.is_active = body.is_active
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/catalog/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent_catalog(
    agent_id: str,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    agent = db.query(AgentCatalog).filter(AgentCatalog.agent_id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    db.delete(agent)
    db.commit()


@router.get("/{agent_id}", response_model=AgentDetailResponse)
def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_readonly),
):
    result = get_agent_detail(db, agent_id)
    if result is None:
        raise HTTPException(status_code=404, detail="agent not found")
    agent, concept_ids = result
    return AgentDetailResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        agent_type=agent.agent_type,
        description=agent.description,
        capabilities=agent.capabilities,
        is_active=agent.is_active,
        concept_ids=concept_ids,
    )
