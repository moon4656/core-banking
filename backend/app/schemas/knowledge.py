from pydantic import BaseModel, ConfigDict, Field


class ConceptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    concept_id: str
    name: str
    description: str | None
    domain: str | None
    is_active: bool


class ConceptDetailResponse(ConceptResponse):
    aliases: list[str]


class ConceptCreateRequest(BaseModel):
    concept_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    domain: str | None = Field(default=None, max_length=100)
    is_active: bool = True
    aliases: list[str] = Field(default_factory=list)


class ConceptUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    domain: str | None = Field(default=None, max_length=100)
    is_active: bool = True
    aliases: list[str] = Field(default_factory=list)


class AliasResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    concept_id: str
    alias: str
    language: str


class AliasCreateRequest(BaseModel):
    concept_id: str = Field(min_length=1, max_length=100)
    alias: str = Field(min_length=1, max_length=200)
    language: str = Field(default="ko", min_length=1, max_length=20)


class AliasUpdateRequest(BaseModel):
    alias: str = Field(min_length=1, max_length=200)
    language: str = Field(default="ko", min_length=1, max_length=20)


class RelationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_concept_id: str
    target_concept_id: str
    relation_type: str
    weight: float


class RelationCreateRequest(BaseModel):
    source_concept_id: str = Field(min_length=1, max_length=100)
    target_concept_id: str = Field(min_length=1, max_length=100)
    relation_type: str = Field(min_length=1, max_length=100)
    weight: float = 1.0


class RelationUpdateRequest(BaseModel):
    source_concept_id: str = Field(min_length=1, max_length=100)
    target_concept_id: str = Field(min_length=1, max_length=100)
    relation_type: str = Field(min_length=1, max_length=100)
    weight: float = 1.0


class AgentMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: str
    concept_id: str
    priority: int


class AgentMappingCreateRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=100)
    concept_id: str = Field(min_length=1, max_length=100)
    priority: int = 0


class AgentMappingUpdateRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=100)
    concept_id: str = Field(min_length=1, max_length=100)
    priority: int = 0


class ConceptApiMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    concept_id: str
    api_id: str
    priority: int


class ConceptApiMappingCreateRequest(BaseModel):
    concept_id: str = Field(min_length=1, max_length=100)
    api_id: str = Field(min_length=1, max_length=100)
    priority: int = 0


class ConceptApiMappingUpdateRequest(BaseModel):
    concept_id: str = Field(min_length=1, max_length=100)
    api_id: str = Field(min_length=1, max_length=100)
    priority: int = 0


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    name: str
    agent_type: str
    description: str | None
    capabilities: list | None


class ApiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    api_id: str
    name: str
    endpoint: str
    method: str
    description: str | None
