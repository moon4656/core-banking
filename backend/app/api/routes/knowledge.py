from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Role, require_admin, require_readonly
from app.knowledge.concept_service import (
    get_agents_by_concept,
    get_all_concepts,
    get_apis_by_concept,
    search_concepts,
)
from app.models.agent_model import AgentCatalog, AgentConceptMapping
from app.models.knowledge_model import (
    ApiCatalog,
    BusinessConcept,
    BusinessConceptRelation,
    BusinessTermAlias,
    ConceptApiMapping,
)
from app.schemas.knowledge import (
    AgentMappingCreateRequest,
    AgentMappingResponse,
    AgentMappingUpdateRequest,
    AgentResponse,
    AliasCreateRequest,
    AliasResponse,
    AliasUpdateRequest,
    ApiResponse,
    ConceptApiMappingCreateRequest,
    ConceptApiMappingResponse,
    ConceptApiMappingUpdateRequest,
    ConceptCreateRequest,
    ConceptDetailResponse,
    ConceptResponse,
    ConceptUpdateRequest,
    RelationCreateRequest,
    RelationResponse,
    RelationUpdateRequest,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


def _build_concept_detail(db: Session, concept: BusinessConcept) -> ConceptDetailResponse:
    aliases = [
        row.alias
        for row in db.query(BusinessTermAlias)
        .filter(BusinessTermAlias.concept_id == concept.concept_id)
        .order_by(BusinessTermAlias.id.asc())
        .all()
    ]
    return ConceptDetailResponse(
        concept_id=concept.concept_id,
        name=concept.name,
        description=concept.description,
        domain=concept.domain,
        is_active=concept.is_active,
        aliases=aliases,
    )


def _get_concept_or_404(db: Session, concept_id: str) -> BusinessConcept:
    concept = (
        db.query(BusinessConcept)
        .filter(BusinessConcept.concept_id == concept_id)
        .first()
    )
    if concept is None:
        raise HTTPException(status_code=404, detail="concept not found")
    return concept


def _get_agent_or_404(db: Session, agent_id: str) -> AgentCatalog:
    agent = db.query(AgentCatalog).filter(AgentCatalog.agent_id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return agent


def _get_api_or_404(db: Session, api_id: str) -> ApiCatalog:
    api = db.query(ApiCatalog).filter(ApiCatalog.api_id == api_id).first()
    if api is None:
        raise HTTPException(status_code=404, detail="api not found")
    return api


@router.get("/concepts", response_model=list[ConceptResponse])
def list_concepts(
    db: Session = Depends(get_db),
    _role: Role = Depends(require_readonly),
):
    return get_all_concepts(db)


@router.get("/concepts/search", response_model=list[ConceptDetailResponse])
def search(
    keyword: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    _role: Role = Depends(require_readonly),
):
    concepts = search_concepts(db, keyword)
    return [_build_concept_detail(db, concept) for concept in concepts]


@router.get("/concepts/{concept_id}", response_model=ConceptDetailResponse)
def get_concept(
    concept_id: str,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_readonly),
):
    concept = _get_concept_or_404(db, concept_id)
    return _build_concept_detail(db, concept)


@router.post(
    "/concepts",
    response_model=ConceptDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_concept(
    body: ConceptCreateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    existing = (
        db.query(BusinessConcept)
        .filter(BusinessConcept.concept_id == body.concept_id)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="concept already exists")

    concept = BusinessConcept(
        concept_id=body.concept_id,
        name=body.name,
        description=body.description,
        domain=body.domain,
        is_active=body.is_active,
    )
    db.add(concept)
    db.flush()

    for alias in dict.fromkeys(alias.strip() for alias in body.aliases if alias.strip()):
        db.add(BusinessTermAlias(concept_id=body.concept_id, alias=alias, language="ko"))

    db.commit()
    db.refresh(concept)
    return _build_concept_detail(db, concept)


@router.put("/concepts/{concept_id}", response_model=ConceptDetailResponse)
def update_concept(
    concept_id: str,
    body: ConceptUpdateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    concept = _get_concept_or_404(db, concept_id)
    concept.name = body.name
    concept.description = body.description
    concept.domain = body.domain
    concept.is_active = body.is_active

    db.query(BusinessTermAlias).filter(
        BusinessTermAlias.concept_id == concept_id
    ).delete(synchronize_session=False)

    for alias in dict.fromkeys(alias.strip() for alias in body.aliases if alias.strip()):
        db.add(BusinessTermAlias(concept_id=concept_id, alias=alias, language="ko"))

    db.commit()
    db.refresh(concept)
    return _build_concept_detail(db, concept)


@router.delete("/concepts/{concept_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_concept(
    concept_id: str,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    concept = _get_concept_or_404(db, concept_id)

    db.query(BusinessTermAlias).filter(
        BusinessTermAlias.concept_id == concept_id
    ).delete(synchronize_session=False)
    db.query(BusinessConceptRelation).filter(
        (BusinessConceptRelation.source_concept_id == concept_id)
        | (BusinessConceptRelation.target_concept_id == concept_id)
    ).delete(synchronize_session=False)
    db.query(AgentConceptMapping).filter(
        AgentConceptMapping.concept_id == concept_id
    ).delete(synchronize_session=False)
    db.query(ConceptApiMapping).filter(
        ConceptApiMapping.concept_id == concept_id
    ).delete(synchronize_session=False)
    db.delete(concept)
    db.commit()


@router.get("/aliases", response_model=list[AliasResponse])
def list_aliases(
    concept_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _role: Role = Depends(require_readonly),
):
    query = db.query(BusinessTermAlias)
    if concept_id:
        query = query.filter(BusinessTermAlias.concept_id == concept_id)
    return query.order_by(BusinessTermAlias.id.asc()).all()


@router.post("/aliases", response_model=AliasResponse, status_code=status.HTTP_201_CREATED)
def create_alias(
    body: AliasCreateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    _get_concept_or_404(db, body.concept_id)
    alias_row = BusinessTermAlias(
        concept_id=body.concept_id,
        alias=body.alias,
        language=body.language,
    )
    db.add(alias_row)
    db.commit()
    db.refresh(alias_row)
    return alias_row


@router.put("/aliases/{alias_id}", response_model=AliasResponse)
def update_alias(
    alias_id: int,
    body: AliasUpdateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    alias_row = db.query(BusinessTermAlias).filter(BusinessTermAlias.id == alias_id).first()
    if alias_row is None:
        raise HTTPException(status_code=404, detail="alias not found")

    alias_row.alias = body.alias
    alias_row.language = body.language
    db.commit()
    db.refresh(alias_row)
    return alias_row


@router.delete("/aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alias(
    alias_id: int,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    alias_row = db.query(BusinessTermAlias).filter(BusinessTermAlias.id == alias_id).first()
    if alias_row is None:
        raise HTTPException(status_code=404, detail="alias not found")
    db.delete(alias_row)
    db.commit()


@router.get("/relations", response_model=list[RelationResponse])
def list_relations(
    concept_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _role: Role = Depends(require_readonly),
):
    query = db.query(BusinessConceptRelation)
    if concept_id:
        query = query.filter(
            (BusinessConceptRelation.source_concept_id == concept_id)
            | (BusinessConceptRelation.target_concept_id == concept_id)
        )
    return query.order_by(BusinessConceptRelation.id.asc()).all()


@router.post("/relations", response_model=RelationResponse, status_code=status.HTTP_201_CREATED)
def create_relation(
    body: RelationCreateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    _get_concept_or_404(db, body.source_concept_id)
    _get_concept_or_404(db, body.target_concept_id)
    relation = BusinessConceptRelation(
        source_concept_id=body.source_concept_id,
        target_concept_id=body.target_concept_id,
        relation_type=body.relation_type,
        weight=body.weight,
    )
    db.add(relation)
    db.commit()
    db.refresh(relation)
    return relation


@router.put("/relations/{relation_id}", response_model=RelationResponse)
def update_relation(
    relation_id: int,
    body: RelationUpdateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    relation = (
        db.query(BusinessConceptRelation)
        .filter(BusinessConceptRelation.id == relation_id)
        .first()
    )
    if relation is None:
        raise HTTPException(status_code=404, detail="relation not found")

    _get_concept_or_404(db, body.source_concept_id)
    _get_concept_or_404(db, body.target_concept_id)
    relation.source_concept_id = body.source_concept_id
    relation.target_concept_id = body.target_concept_id
    relation.relation_type = body.relation_type
    relation.weight = body.weight
    db.commit()
    db.refresh(relation)
    return relation


@router.delete("/relations/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relation(
    relation_id: int,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    relation = (
        db.query(BusinessConceptRelation)
        .filter(BusinessConceptRelation.id == relation_id)
        .first()
    )
    if relation is None:
        raise HTTPException(status_code=404, detail="relation not found")
    db.delete(relation)
    db.commit()


@router.get("/agent-mappings", response_model=list[AgentMappingResponse])
def list_agent_mappings(
    concept_id: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _role: Role = Depends(require_readonly),
):
    query = db.query(AgentConceptMapping)
    if concept_id:
        query = query.filter(AgentConceptMapping.concept_id == concept_id)
    if agent_id:
        query = query.filter(AgentConceptMapping.agent_id == agent_id)
    return query.order_by(AgentConceptMapping.id.asc()).all()


@router.post(
    "/agent-mappings",
    response_model=AgentMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_mapping(
    body: AgentMappingCreateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    _get_agent_or_404(db, body.agent_id)
    _get_concept_or_404(db, body.concept_id)
    existing = (
        db.query(AgentConceptMapping)
        .filter_by(agent_id=body.agent_id, concept_id=body.concept_id)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="agent mapping already exists")
    mapping = AgentConceptMapping(
        agent_id=body.agent_id,
        concept_id=body.concept_id,
        priority=body.priority,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


@router.put("/agent-mappings/{mapping_id}", response_model=AgentMappingResponse)
def update_agent_mapping(
    mapping_id: int,
    body: AgentMappingUpdateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    mapping = db.query(AgentConceptMapping).filter(AgentConceptMapping.id == mapping_id).first()
    if mapping is None:
        raise HTTPException(status_code=404, detail="agent mapping not found")

    _get_agent_or_404(db, body.agent_id)
    _get_concept_or_404(db, body.concept_id)
    mapping.agent_id = body.agent_id
    mapping.concept_id = body.concept_id
    mapping.priority = body.priority
    db.commit()
    db.refresh(mapping)
    return mapping


@router.delete("/agent-mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    mapping = db.query(AgentConceptMapping).filter(AgentConceptMapping.id == mapping_id).first()
    if mapping is None:
        raise HTTPException(status_code=404, detail="agent mapping not found")
    db.delete(mapping)
    db.commit()


@router.get("/concept-api-mappings", response_model=list[ConceptApiMappingResponse])
def list_concept_api_mappings(
    concept_id: str | None = Query(default=None),
    api_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _role: Role = Depends(require_readonly),
):
    query = db.query(ConceptApiMapping)
    if concept_id:
        query = query.filter(ConceptApiMapping.concept_id == concept_id)
    if api_id:
        query = query.filter(ConceptApiMapping.api_id == api_id)
    return query.order_by(ConceptApiMapping.id.asc()).all()


@router.post(
    "/concept-api-mappings",
    response_model=ConceptApiMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_concept_api_mapping(
    body: ConceptApiMappingCreateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    _get_concept_or_404(db, body.concept_id)
    _get_api_or_404(db, body.api_id)
    mapping = ConceptApiMapping(
        concept_id=body.concept_id,
        api_id=body.api_id,
        priority=body.priority,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


@router.put("/concept-api-mappings/{mapping_id}", response_model=ConceptApiMappingResponse)
def update_concept_api_mapping(
    mapping_id: int,
    body: ConceptApiMappingUpdateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    mapping = db.query(ConceptApiMapping).filter(ConceptApiMapping.id == mapping_id).first()
    if mapping is None:
        raise HTTPException(status_code=404, detail="concept api mapping not found")

    _get_concept_or_404(db, body.concept_id)
    _get_api_or_404(db, body.api_id)
    mapping.concept_id = body.concept_id
    mapping.api_id = body.api_id
    mapping.priority = body.priority
    db.commit()
    db.refresh(mapping)
    return mapping


@router.delete("/concept-api-mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_concept_api_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    mapping = db.query(ConceptApiMapping).filter(ConceptApiMapping.id == mapping_id).first()
    if mapping is None:
        raise HTTPException(status_code=404, detail="concept api mapping not found")
    db.delete(mapping)
    db.commit()


@router.get("/concepts/{concept_id}/agents", response_model=list[AgentResponse])
def list_agents_for_concept(
    concept_id: str,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_readonly),
):
    agents = get_agents_by_concept(db, concept_id)
    if agents is None:
        raise HTTPException(status_code=404, detail="concept not found")
    return agents


@router.get("/concepts/{concept_id}/apis", response_model=list[ApiResponse])
def list_apis_for_concept(
    concept_id: str,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_readonly),
):
    apis = get_apis_by_concept(db, concept_id)
    if apis is None:
        raise HTTPException(status_code=404, detail="concept not found")
    return apis
