from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB as JSON

from app.core.database import Base


class AgentCatalog(Base):
    __tablename__ = "agent_catalog"
    __table_args__ = {"comment": "AI Agent 메타데이터 등록 테이블. 어떤 Agent가 있고 어떤 역할을 하는지 정의한다. is_active=False이면 라우팅에서 제외된다. 새 Agent 추가 시 이 테이블과 AgentConceptMapping에 레코드를 삽입한다."}

    id           = Column(Integer, primary_key=True, index=True, comment="PK")
    agent_id     = Column(String(100), unique=True, nullable=False, index=True, comment="시스템 고유 식별자 (예: RATE_AGENT)")
    name         = Column(String(200), nullable=False, comment="Agent 이름 (예: 금리 전문 Agent)")
    agent_type   = Column(String(50), nullable=False, comment="Agent 종류: leader / product / rate / policy / search")
    description  = Column(Text, nullable=True, comment="Agent 역할 및 처리 범위 설명")
    capabilities = Column(JSON, nullable=True, comment="처리 가능한 작업 목록 JSON 배열 (참고용)")
    is_active    = Column(Boolean, default=True, nullable=False, comment="False이면 라우팅 대상에서 제외")
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class AgentConceptMapping(Base):
    __tablename__ = "agent_concept_mapping"
    __table_args__ = {"comment": "Agent와 업무 개념(concept)을 연결하는 매핑 테이블. 'RATE_AGENT는 CONCEPT_INTEREST_RATE를 처리한다'는 라우팅 규칙을 DB에 저장한다. Leader Agent는 탐지된 concept_id로 이 테이블을 조회해 실행할 Agent를 결정한다."}

    id         = Column(Integer, primary_key=True, index=True, comment="PK")
    agent_id   = Column(String(100), ForeignKey("agent_catalog.agent_id"), nullable=False, index=True, comment="FK → agent_catalog.agent_id")
    concept_id = Column(String(100), ForeignKey("business_concept.concept_id"), nullable=False, index=True, comment="FK → business_concept.concept_id")
    priority   = Column(Integer, default=0, nullable=False, comment="동일 concept에 복수 Agent 매핑 시 우선순위 — 낮을수록 먼저 선택")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")
