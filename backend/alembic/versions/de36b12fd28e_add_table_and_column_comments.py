"""add_table_and_column_comments

Revision ID: de36b12fd28e
Revises: 0010
Create Date: 2026-06-15 05:04:36.850417

"""
from alembic import op
import sqlalchemy as sa

revision = 'de36b12fd28e'
down_revision = '0010'
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# 테이블별 comment 정의 (table_name → comment)
# ---------------------------------------------------------------------------
TABLE_COMMENTS = {
    "business_concept":
        "업무 개념 단위. 금리·대출상품 등 도메인 지식의 핵심 노드. "
        "concept_id는 시스템 고유 식별자(예: CONCEPT_INTEREST_RATE), "
        "is_active=False이면 검색·라우팅에서 제외된다.",
    "business_term_alias":
        "업무 개념의 동의어·별칭. '이자율'로 검색해도 CONCEPT_INTEREST_RATE를 찾을 수 있도록 "
        "별도 테이블로 관리한다. 개념명 변경 없이 alias만 추가·삭제 가능.",
    "business_concept_relation":
        "업무 개념 간 관계(온톨로지 엣지). weight≥0.7인 관계는 Leader Agent가 탐지된 concept을 "
        "자동 확장할 때 사용한다. MVP에서는 수동 등록만 허용하며 자동 추론은 구현하지 않는다.",
    "data_source_catalog":
        "데이터 소스 카탈로그. DB 테이블·파일·외부 시스템 등 데이터 출처를 등록한다. "
        "ConceptDataMapping을 통해 특정 concept과 연결.",
    "api_catalog":
        "Tool Hub가 호출할 수 있는 API(Tool) 목록. endpoint·method로 실제 HTTP 요청을 수행하며, "
        "is_active=False이면 호출하지 않는다. 새 Mock API 추가 시 이 테이블과 ConceptApiMapping에 레코드를 삽입한다.",
    "concept_data_mapping":
        "업무 개념(concept)과 데이터 소스를 연결하는 매핑 테이블. "
        "field_path로 소스 내 특정 필드를 지정하고, priority로 다중 소스 간 우선순위를 제어한다.",
    "concept_api_mapping":
        "업무 개념(concept)과 호출 가능한 API를 연결하는 매핑 테이블. "
        "Leader Agent가 탐지된 concept_id로 어떤 API를 호출할지 결정할 때 참조하며, priority로 호출 순서를 제어한다.",
    "agent_catalog":
        "AI Agent 메타데이터 등록 테이블. 어떤 Agent가 있고 어떤 역할을 하는지 정의한다. "
        "is_active=False이면 라우팅에서 제외된다. 새 Agent 추가 시 이 테이블과 AgentConceptMapping에 레코드를 삽입한다.",
    "agent_concept_mapping":
        "Agent와 업무 개념(concept)을 연결하는 매핑 테이블. "
        "'RATE_AGENT는 CONCEPT_INTEREST_RATE를 처리한다'는 라우팅 규칙을 DB에 저장한다. "
        "Leader Agent는 탐지된 concept_id로 이 테이블을 조회해 실행할 Agent를 결정한다.",
    "leader_decision":
        "Leader Agent 라우팅 판단 감사 로그. 요청 1건당 1행을 기록하며 "
        "AI 설명 가능성(Explainability)·규정 준수(Compliance) 요구사항을 충족한다. "
        "request_id로 TraceEvent와 조인해 전체 처리 흐름을 추적할 수 있다.",
    "trace_event":
        "요청 처리 단계별 이벤트 로그. request_id로 단일 요청의 전체 처리 흐름을 재현할 수 있다. "
        "디버깅·성능 분석·감사(Audit)에 활용하며, 요청 1건당 여러 행이 기록된다.",
    "evidence_reference":
        "Tool 호출로 획득한 실제 데이터 근거. AI 응답의 출처를 추적하고 신뢰도를 정량화한다. "
        "confidence_score = 0.5×data_quality + 0.4×intent_relevance + 0.1×latency_bonus 로 산출한다.",
    "ai_decision_trace":
        "요청 1건의 최상위 Decision Trace 요약. 운영자 화면(Summary / Evidence View)이 공통으로 참조하는 엔트리다. "
        "request_id는 UNIQUE이며 메타데이터·memory·intent·latency를 JSONB로 통합 저장한다.",
    "ai_concept_detection":
        "Concept 탐지 결과를 concept 단위로 저장하는 테이블. "
        "직접 탐지(direct)와 온톨로지 확장(expanded)을 구분하고, 신뢰도·소스·이유를 각 행에 기록한다.",
    "ai_agent_selection":
        "Agent 후보별 선택·미선택 사유 기록. selected=False 행도 저장해 왜 제외됐는지 사후에 추적할 수 있다. "
        "Decision Rule 평가 결과(role·execution_mode·tools_assigned·decision_rule_ids)도 포함한다.",
    "ai_tool_execution":
        "Tool 실행 1건 로그. 운영자 화면에서 input/output 요약·상태·latency·연결 evidence를 표시한다. "
        "request 단위 Tool 실행 이력을 추적하는 용도.",
    "ai_reranking_trace":
        "Re-ranking 결과 1건. request_id는 UNIQUE. "
        "criteria_weights와 후보별 score breakdown을 JSONB로 저장해 어떤 근거가 최종 답변에 선택됐는지 추적한다.",
    "ai_final_answer_trace":
        "최종 답변과 grounding 메타데이터 1건. request_id는 UNIQUE. "
        "어떤 Evidence를 근거로 답변이 생성됐는지 추적하는 용도.",
    "leader_decision_node":
        "Decision Graph의 노드 1개. request_id 기준으로 Leader Agent 판단 단계(의도 분석·Concept 탐지·"
        "Agent 선택·Tool 호출·최종 답변)를 각 1행으로 기록한다. "
        "data JSONB에 단계별 상세 정보를 저장해 그래프 API에서 조인 없이 응답 가능.",
    "leader_decision_edge":
        "Decision Graph의 엣지 1개 (source_node → target_node). edge_type으로 관계 의미를 구분한다: "
        "HAS_INTENT / INFLUENCES / DETECTS / HANDLED_BY / SELECTS / CALLS / RETURNS / SCORED_BY / SUPPORTS / PRODUCES",
    "leader_decision_review":
        "Reviewer(사람)가 Decision Graph 1건을 검토한 결과. "
        "의도 정확성·Concept 완전성·Agent 선택·Evidence 충분성·답변 적절성을 Boolean으로 평가한다. "
        "request_id는 UNIQUE — 1건당 최신 리뷰 1개만 유지.",
}

# ---------------------------------------------------------------------------
# 컬럼별 comment 정의 (table_name → {column_name → comment})
# ---------------------------------------------------------------------------
COLUMN_COMMENTS = {
    "business_concept": {
        "id": "PK",
        "concept_id": "시스템 내부 고유 식별자 (예: CONCEPT_INTEREST_RATE)",
        "name": "사람이 읽는 개념 이름 (예: 금리)",
        "description": "개념 설명",
        "domain": "소속 도메인 (loan / rate / policy / document / counseling / customer)",
        "is_active": "False이면 검색·라우팅 제외",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "business_term_alias": {
        "id": "PK",
        "concept_id": "FK → business_concept.concept_id",
        "alias": "동의어·별칭 문자열 (예: 이자율, 대출금리)",
        "language": "언어 코드 (현재 ko만 사용)",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "business_concept_relation": {
        "id": "PK",
        "source_concept_id": "관계 출발 concept (FK → business_concept.concept_id)",
        "target_concept_id": "관계 도착 concept (FK → business_concept.concept_id)",
        "relation_type": "관계 유형: includes / requires / governed_by / has_condition / has_record",
        "weight": "관계 강도 (0.0~1.0). 0.7 미만이면 자동 확장에서 제외",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "data_source_catalog": {
        "id": "PK",
        "source_id": "시스템 고유 식별자 (예: DS_LOAN_TABLE)",
        "name": "데이터 소스 이름",
        "source_type": "소스 종류: postgresql / file / api",
        "connection_info": '접속 정보 JSON (예: {"table": "loan_products"})',
        "is_active": "False이면 조회 대상에서 제외",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "api_catalog": {
        "id": "PK",
        "api_id": "시스템 고유 식별자 (예: MOCK_RATE_LOOKUP)",
        "name": "API 이름",
        "endpoint": "HTTP 요청 URL (예: http://mock-api:8010/rates)",
        "method": "HTTP 메서드 (GET / POST)",
        "description": "API 기능 설명",
        "request_schema": "요청 파라미터 JSON Schema (참고용)",
        "response_schema": "응답 구조 JSON Schema (참고용)",
        "is_active": "False이면 Tool Hub가 이 API를 호출하지 않음",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "concept_data_mapping": {
        "id": "PK",
        "concept_id": "FK → business_concept.concept_id",
        "source_id": "FK → data_source_catalog.source_id",
        "field_path": "소스 내 필드 경로 (예: loan_products.interest_rate)",
        "priority": "우선순위 — 낮을수록 먼저 사용",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "concept_api_mapping": {
        "id": "PK",
        "concept_id": "FK → business_concept.concept_id",
        "api_id": "FK → api_catalog.api_id",
        "priority": "우선순위 — 낮을수록 먼저 호출",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "agent_catalog": {
        "id": "PK",
        "agent_id": "시스템 고유 식별자 (예: RATE_AGENT)",
        "name": "Agent 이름 (예: 금리 전문 Agent)",
        "agent_type": "Agent 종류: leader / product / rate / policy / search",
        "description": "Agent 역할 및 처리 범위 설명",
        "capabilities": "처리 가능한 작업 목록 JSON 배열 (참고용)",
        "is_active": "False이면 라우팅 대상에서 제외",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "agent_concept_mapping": {
        "id": "PK",
        "agent_id": "FK → agent_catalog.agent_id",
        "concept_id": "FK → business_concept.concept_id",
        "priority": "동일 concept에 복수 Agent 매핑 시 우선순위 — 낮을수록 먼저 선택",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "leader_decision": {
        "id": "PK",
        "request_id": "요청 고유 ID (TraceEvent와 공유)",
        "detected_intent": "LLM이 분류한 의도: INQUIRY / COMPARISON / RECOMMENDATION / APPLICATION / OTHER",
        "detected_concepts": '온톨로지 확장 후 최종 concept 목록 (예: ["CONCEPT_INTEREST_RATE"])',
        "direct_concepts": "키워드 직접 매칭으로 탐지된 concept 목록",
        "expanded_concepts": "온톨로지 관계 확장으로 추가된 concept 목록",
        "selected_agents": '라우팅된 Agent ID 목록 (예: ["RATE_AGENT"])',
        "reasoning": "intent_data 전체 JSON — LLM 분류 근거",
        "confidence_score": "라우팅 신뢰도 (성공한 API 결과 수 / 전체 API 수)",
        "total_steps": "생성된 ExecutionStep 수",
        "memory_turns": "Short Memory에서 로드한 대화 턴 수",
        "ltm_turns": "Long-Term Memory에서 로드한 턴 수",
        "answer": "최종 LLM 생성 답변 전문",
        "review_reason": "검토 필요 원인 코드 (NEEDS_REVIEW / FAIL 등)",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "trace_event": {
        "id": "PK",
        "request_id": "요청 고유 ID",
        "event_type": (
            "이벤트 유형: REQUEST_RECEIVED / MEMORY_LOADED / INTENT_ANALYZED / "
            "CONCEPT_DETECTED / AGENT_SELECTED / PLAN_CREATED / RESULTS_RERANKED / "
            "TOOL_INVOKED / RESPONSE_COMPLETED"
        ),
        "agent_id": "이벤트를 발생시킨 Agent ID (해당 없으면 NULL)",
        "tool_id": "이벤트와 연관된 Tool ID (해당 없으면 NULL)",
        "input_data": "해당 단계의 입력값 JSON",
        "output_data": "해당 단계의 출력값 JSON",
        "status": "처리 결과: success / error",
        "duration_ms": "해당 단계 처리 시간 (밀리초)",
        "created_at": "이벤트 발생 일시 (UTC)",
    },
    "evidence_reference": {
        "id": "PK",
        "request_id": "요청 고유 ID",
        "concept_id": "이 근거가 해당하는 업무 개념 ID",
        "source_type": "근거 출처 유형 (예: api)",
        "source_id": "근거를 제공한 API ID (예: MOCK_RATE_LOOKUP)",
        "content": "API 응답 원본 데이터 JSON",
        "confidence_score": "최종 종합 신뢰도 (0.0~1.0)",
        "data_quality_score": "데이터 완성도 점수 — 필수 필드 존재 여부·항목 수 기반 (가중치 50%)",
        "intent_relevance_score": "사용자 의도와의 관련도 점수 (가중치 40%)",
        "response_latency_ms": "API 응답 시간 (ms) — 2초 이내이면 latency_bonus 1.0 적용",
        "item_count": "API가 반환한 데이터 레코드 수 (단건=1, 목록=N)",
        "quality_flags": '세부 품질 체크 결과 (예: {"has_annual_rate": true})',
        "related_evidence_ids": "온톨로지 관계로 연결된 다른 EvidenceReference.id 목록",
        "agent_id": "이 근거를 생성한 Sub-Agent ID",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "ai_decision_trace": {
        "id": "PK",
        "request_id": "요청 고유 ID (UNIQUE)",
        "session_id": "Redis Short Memory 세션 ID",
        "owner_name": "요청한 사용자 이름",
        "owner_role": "요청한 사용자 역할: ADMIN / ANALYST / READONLY",
        "user_query": "사용자 원본 질문",
        "normalized_query": "정규화·전처리된 질문",
        "request_meta": "요청 메타데이터 JSONB (헤더, 클라이언트 정보 등)",
        "memory_summary": "Short/Long Memory 로드 요약 JSONB",
        "intent_analysis": "의도 분석 결과 전체 JSONB",
        "latency": "단계별 처리 시간 집계 JSONB",
        "status": "처리 상태: completed / error / timeout",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "ai_concept_detection": {
        "id": "PK",
        "request_id": "요청 고유 ID",
        "concept_id": "탐지된 concept ID",
        "detection_stage": "탐지 단계: direct / expanded",
        "confidence": "탐지 신뢰도 (0.0~1.0)",
        "source_type": "탐지 소스 유형: alias / keyword / relation",
        "source_terms": "매칭된 alias·키워드 목록 JSONB",
        "relation_path": "온톨로지 확장 경로 JSONB (expanded일 때)",
        "reason": "탐지 근거 설명",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "ai_agent_selection": {
        "id": "PK",
        "request_id": "요청 고유 ID",
        "agent_id": "평가 대상 Agent ID",
        "selected": "최종 선택 여부",
        "score": "선택 점수",
        "matched_concepts": "이 Agent와 매칭된 concept ID 목록 JSONB",
        "reason": "선택 근거",
        "rejection_reason": "미선택 이유 (selected=False일 때)",
        "role": "Decision Rule 평가 결과 — Agent 역할",
        "execution_mode": "실행 모드 (예: parallel / sequential)",
        "tools_assigned": "이 Agent에 배정된 Tool 목록 JSONB",
        "decision_rule_ids": "적용된 Decision Rule ID 목록 JSONB",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "ai_tool_execution": {
        "id": "PK",
        "request_id": "요청 고유 ID",
        "agent_id": "Tool을 호출한 Agent ID",
        "tool_code": "실행된 Tool 코드 (api_catalog.api_id)",
        "concept_ids": "이 Tool 실행과 연관된 concept ID 목록 JSONB",
        "input_summary": "Tool 입력 요약",
        "output_summary": "Tool 출력 요약",
        "status": "실행 결과: success / error / timeout",
        "latency_ms": "Tool 응답 시간 (ms)",
        "error_summary": "에러 발생 시 오류 메시지 요약",
        "evidence_ids": "이 실행으로 생성된 EvidenceReference.id 목록 JSONB",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "ai_reranking_trace": {
        "id": "PK",
        "request_id": "요청 고유 ID (UNIQUE)",
        "criteria_weights": "재정렬 기준 가중치 JSONB",
        "candidates": "재정렬 후보 및 점수 상세 JSONB",
        "selected_evidence_ids": "최종 선택된 EvidenceReference.id 목록 JSONB",
        "reason": "재정렬 결과 설명",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "ai_final_answer_trace": {
        "id": "PK",
        "request_id": "요청 고유 ID (UNIQUE)",
        "answer": "최종 LLM 생성 답변 전문",
        "answer_summary": "답변 요약 (UI 미리보기용)",
        "used_evidence_ids": "답변 생성에 사용된 EvidenceReference.id 목록 JSONB",
        "grounding_summary": "근거(grounding) 설명 요약",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "leader_decision_node": {
        "id": "PK",
        "request_id": "요청 고유 ID",
        "node_id": "노드 고유 ID (예: req-xxx::intent)",
        "node_type": "노드 유형: intent / concept / agent / tool / answer 등",
        "node_label": "그래프 UI 표시용 라벨",
        "status": "노드 처리 결과: SUCCESS / ERROR / SKIP",
        "sequence_order": "처리 순서 (낮을수록 먼저 실행)",
        "position_x": "그래프 UI 노드 X 좌표",
        "position_y": "그래프 UI 노드 Y 좌표",
        "data": "단계별 상세 정보 JSONB",
        "style": "그래프 UI 스타일 JSONB",
        "duration_ms": "이 노드 처리 시간 (ms)",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "leader_decision_edge": {
        "id": "PK",
        "request_id": "요청 고유 ID",
        "edge_id": "엣지 고유 ID",
        "edge_type": "엣지 유형: HAS_INTENT / DETECTS / SELECTS / CALLS / RETURNS 등",
        "edge_label": "그래프 UI 표시용 라벨",
        "source_node_id": "출발 노드 ID (FK 논리적 참조 → leader_decision_node.node_id)",
        "target_node_id": "도착 노드 ID (FK 논리적 참조 → leader_decision_node.node_id)",
        "data": "엣지 부가 정보 JSONB",
        "style": "그래프 UI 스타일 JSONB",
        "weight": "엣지 가중치 (시각화·필터링용)",
        "created_at": "레코드 생성 일시 (UTC)",
    },
    "leader_decision_review": {
        "id": "PK",
        "request_id": "요청 고유 ID (UNIQUE)",
        "reviewer_id": "검토자 식별자",
        "status": "검토 상태: PENDING / IN_REVIEW / DONE",
        "overall_result": "종합 결과: PASS / FAIL / NEEDS_REVIEW",
        "intent_correct": "의도 분류 정확성 평가",
        "concept_complete": "Concept 탐지 완전성 평가",
        "agent_correct": "Agent 선택 정확성 평가",
        "evidence_sufficient": "Evidence 충분성 평가",
        "answer_appropriate": "최종 답변 적절성 평가",
        "missing_concepts": "누락된 concept 목록",
        "wrong_agents": "잘못 선택된 Agent 목록",
        "comment": "검토자 코멘트",
        "review_score": "종합 점수 (0.0~1.0)",
        "reviewed_at": "검토 완료 일시 (UTC)",
        "created_at": "레코드 생성 일시 (UTC)",
    },
}


def upgrade() -> None:
    for table, comment in TABLE_COMMENTS.items():
        op.create_table_comment(table, comment, existing_comment=None, schema=None)

    for table, columns in COLUMN_COMMENTS.items():
        for col, comment in columns.items():
            op.execute(
                sa.text(f"COMMENT ON COLUMN {table}.{col} IS :cmt").bindparams(cmt=comment)
            )


def downgrade() -> None:
    for table in TABLE_COMMENTS:
        op.drop_table_comment(table, existing_comment=None, schema=None)

    for table, columns in COLUMN_COMMENTS.items():
        for col in columns:
            op.execute(sa.text(f"COMMENT ON COLUMN {table}.{col} IS NULL"))
