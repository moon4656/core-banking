from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime
import uuid

from app.core.database import Base


class ConceptEvalCustomQuery(Base):
    """사용자가 직접 추가한 평가 질의. 새로고침 후에도 유지됨."""
    __tablename__ = "concept_eval_custom_query"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    category        = Column(String(100), nullable=False)
    message         = Column(Text, nullable=False)
    expected_agents = Column(ARRAY(String), nullable=False, default=list)
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(),
                             onupdate=func.now(), nullable=False)


class ConceptEvalRun(Base):
    """Concept 탐지 평가 실행 요약. 평가 1회당 1행."""
    __tablename__ = "concept_eval_run"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    run_id        = Column(String(36), unique=True, nullable=False,
                           default=lambda: str(uuid.uuid4()), index=True)
    run_at        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    run_type      = Column(String(20), nullable=False)   # ALL | SELECTED
    category      = Column(String(100), nullable=True)   # None = 전체
    total_queries = Column(Integer, nullable=False)
    avg_f1        = Column(Float, nullable=True)
    overall_grade = Column(String(2), nullable=False)
    summary_json  = Column(JSONB, nullable=True)         # by_category 등 전체 summary 보관

    items = relationship("ConceptEvalItem", back_populates="run",
                         cascade="all, delete-orphan", lazy="dynamic")


class ConceptEvalItem(Base):
    """평가 실행의 개별 질의 결과. run 1건당 N행."""
    __tablename__ = "concept_eval_item"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    run_id            = Column(String(36), ForeignKey("concept_eval_run.run_id",
                               ondelete="CASCADE"), nullable=False, index=True)
    category          = Column(String(100), nullable=False)
    message           = Column(Text, nullable=False)
    expected_agents   = Column(ARRAY(String), nullable=False, default=list)
    detected_concepts = Column(ARRAY(String), nullable=False, default=list)
    routed_agents     = Column(ARRAY(String), nullable=False, default=list)
    true_positive     = Column(ARRAY(String), nullable=False, default=list)
    false_positive    = Column(ARRAY(String), nullable=False, default=list)
    false_negative    = Column(ARRAY(String), nullable=False, default=list)
    precision         = Column(Float, nullable=True)
    recall            = Column(Float, nullable=True)
    f1_score          = Column(Float, nullable=True)
    grade             = Column(String(2), nullable=False)

    run = relationship("ConceptEvalRun", back_populates="items")
