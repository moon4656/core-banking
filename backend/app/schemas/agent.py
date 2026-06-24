from pydantic import BaseModel, ConfigDict, Field


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    name: str
    agent_type: str
    description: str | None
    capabilities: list | None
    is_active: bool


class AgentCreateRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    agent_type: str = Field(min_length=1, max_length=50)
    description: str | None = None
    capabilities: list | None = None
    is_active: bool = True


class AgentUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    agent_type: str = Field(min_length=1, max_length=50)
    description: str | None = None
    capabilities: list | None = None
    is_active: bool = True


class AgentDetailResponse(AgentResponse):
    concept_ids: list[str]


class AgentRouteItem(BaseModel):
    agent_id: str
    agent_type: str
    name: str
    concept_ids: list[str]


class AgentRouteRequest(BaseModel):
    concept_ids: list[str]


class AgentRouteResponse(BaseModel):
    routing: list[AgentRouteItem]
    unrouted_concept_ids: list[str]
