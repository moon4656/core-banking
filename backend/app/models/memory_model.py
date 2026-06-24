# memory_model.py — Long-term Memory 테이블 정의
#
# [Short Memory와의 차이]
#   Short Memory (Redis) : 최근 5턴, TTL 1시간, 원문 메시지 그대로 저장
#   Long-term Memory (DB): 영구 보존, 턴별 요약(의도 + 핵심 개념 + 질문/답변 요약) 저장
#
# [활용 목적]
#   - Redis TTL(1시간) 만료 후에도 과거 상담 패턴을 LLM 컨텍스트로 활용
#   - 반복 질문 탐지, 사용자 관심 concept 파악
#   - 장기 세션에서 일관성 있는 답변 품질 유지
#
# [저장 단위]
#   턴(turn) 단위 — 질문 1개 + 답변 1개 = 1 레코드
#   질문·답변은 최대 300/500자로 잘라 요약 형태로 저장한다.

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB as JSON

from app.core.database import Base


class LongTermMemory(Base):
    """
    세션별 대화 턴 요약을 영구 저장하는 테이블.

    [주요 필드]
    session_id        : 대화 세션 식별자 (Short Memory의 session_id와 동일)
    user_id           : 사용자 식별자 (선택)
    turn_index        : 이 세션 내 몇 번째 턴인지 (0-based)
    intent            : 이 턴에서 탐지된 의도 (INQUIRY/COMPARISON 등)
    detected_concepts : 탐지된 Concept ID 목록
    keywords          : 의도 분석에서 추출한 핵심 키워드
    question_summary  : 사용자 질문 요약 (최대 300자)
    answer_summary    : AI 답변 요약 (최대 500자)
    created_at        : 저장 시각
    """
    __tablename__ = "long_term_memory"

    id                = Column(Integer, primary_key=True, index=True)
    session_id        = Column(String(100), nullable=False, index=True)
    user_id           = Column(String(100), nullable=True,  index=True)
    turn_index        = Column(Integer, default=0, nullable=False)

    intent            = Column(String(50),  nullable=True)   # "INQUIRY", "COMPARISON" 등
    detected_concepts = Column(JSON,        nullable=True)   # ["CONCEPT_INTEREST_RATE", ...]
    keywords          = Column(JSON,        nullable=True)   # ["신용대출", "금리", ...]
    question_summary  = Column(Text,        nullable=True)   # 질문 원문 (최대 300자)
    answer_summary    = Column(Text,        nullable=True)   # 답변 요약 (최대 500자)

    created_at        = Column(DateTime, default=datetime.utcnow, nullable=False)
