# schemas/ai_gateway.py — Chat API 요청/응답 스키마 정의
#
# [요청 → 응답 흐름]
#
#   ChatRequest (입력)
#       ↓ POST /api/v1/ai/chat
#   LeaderAgent.run()
#       ├─ Short Memory 로드
#       ├─ 의도 분석 → IntentData
#       ├─ Concept 탐지 + 온톨로지 확장 → ExecutionPlan
#       ├─ Tool 실행 → StepResult 목록
#       ├─ Re-ranking → ranked_results
#       └─ LLM 요약 → answer
#   ChatResponse (출력)

from pydantic import BaseModel, Field

from app.schemas.decision_trace import LeaderDecisionV2


class ChatRequest(BaseModel):
    """
    Chat API 입력 스키마.

    message   : 사용자가 입력한 자연어 질문
    session_id: 다중 턴 대화 세션 식별자.
                같은 session_id로 반복 요청하면 이전 대화를 기억한다.
                없으면 매 요청이 독립적으로 처리된다.
    channel   : 요청 채널 (예: "web", "mobile", "kakao", "call_center").
                채널별 응답 스타일 또는 접근 통계에 활용한다.
    user_id   : 사용자 식별자. 미인증 접근 시 None.
                로그인된 사용자의 개인화 서비스에 활용한다.
    """
    message: str
    session_id: str | None = None
    channel: str = "web"               # 기본값: web 채널
    user_id: str | None = None         # 미인증 시 None


class ExecutionStep(BaseModel):
    """
    실행 계획의 단일 단계.

    step_index : 실행 순서 (0부터 시작)
    agent_id   : 이 단계를 담당하는 Sub-Agent
    concept_id : 이 단계가 처리하는 업무 개념
    api_id     : 실제 호출할 API (Tool Hub가 이 id로 ApiCatalog를 조회)
    params     : API 호출 파라미터 (MVP에서는 빈 dict)
    """
    step_index: int
    agent_id: str
    concept_id: str
    api_id: str
    params: dict


class ExecutionPlan(BaseModel):
    """
    Leader Agent가 생성한 실행 계획 전체.

    detected_concepts : 탐지된 개념 + 온톨로지 확장된 개념 모두 포함
    routed_agents     : 배정된 Sub-Agent 목록
    steps             : 순서대로 실행할 API 호출 단계 목록
    """
    request_id: str
    message: str
    detected_concepts: list[str]
    routed_agents: list[str]
    steps: list[ExecutionStep]


class StepResult(BaseModel):
    """
    ExecutionStep 하나의 실행 결과.

    status : "success" 또는 "error"
    data   : API 응답 JSON (성공 시)
    error  : 오류 메시지 (실패 시)
    """
    step_index: int = 0  # Sub Agent 경로에서 생성 시 순서 정보가 없을 수 있어 기본값 허용
    api_id: str
    status: str
    data: dict | list | None
    error: str | None


class LeaderResult(BaseModel):
    """
    Leader Agent 실행 결과 내부 데이터 클래스.

    raw_results    : Tool 호출 원본 결과 (순서 변경 전)
    ranked_results : Re-ranking 적용 후 관련도 순 결과
    intent         : LLM이 분석한 사용자 의도 데이터
    memory_turns   : 이번 요청에서 로드한 이전 대화 턴 수
    answer         : 최종 한국어 답변
    decision_v2    : v2 Decision Schema (Concept 분류·Agent 선택 사유 포함)
    """
    plan: "ExecutionPlan"
    raw_results: list[StepResult]
    ranked_results: list[StepResult]
    intent: dict
    memory_turns: int
    answer: str
    decision_v2: LeaderDecisionV2 | None = None
    needs_clarification:    bool = False
    clarification_question: str | None = None


class ScenarioItem(BaseModel):
    """
    사전 정의된 Chat 테스트 시나리오 1건.

    id                : 시나리오 고유 ID (예: FX-001)
    category          : 분류 (forex / notification / loan / rate / policy / document)
    agent             : 이 시나리오를 주로 처리하는 Sub-Agent ID
    intent            : 기대 의도 유형 (INQUIRY / COMPARISON / RECOMMENDATION / APPLICATION)
    message           : Chat API에 그대로 전송할 예시 질문
    description       : 시나리오 설명 및 검증 포인트
    expected_concepts : 이 질문에서 탐지돼야 할 핵심 Concept ID 목록
    expected_api      : 주로 호출될 것으로 기대하는 Tool/API ID
    tags              : 추가 검색용 자유 태그
    """
    id: str
    category: str
    agent: str
    intent: str
    message: str
    description: str
    expected_concepts: list[str] = Field(default_factory=list)
    expected_api: str | None = None
    tags: list[str] = Field(default_factory=list)


class ScenarioListResponse(BaseModel):
    """시나리오 목록 응답."""
    total: int
    categories: list[str]
    scenarios: list[ScenarioItem]


class ChatResponse(BaseModel):
    """
    Chat API 최종 응답 스키마.

    plan           : 실행 계획 (디버깅/투명성용)
    results        : Re-ranking 적용된 API 호출 결과 목록
    answer         : 사용자에게 보여줄 최종 한국어 답변
    intent         : 탐지된 질문 유형 (INQUIRY/COMPARISON/RECOMMENDATION/APPLICATION/OTHER)
    memory_turns   : 이번 답변에 활용된 이전 대화 턴 수 (0이면 새 대화)
    trace_count    : 처리 단계 기록 건수
    evidence_count : 데이터 근거 기록 건수
    decision_v2    : v2 Decision Schema (Concept 분류·Agent 선택/미선택 사유 포함)
    """
    request_id: str
    message: str
    plan: ExecutionPlan
    results: list[StepResult]
    answer: str
    intent: dict
    memory_turns: int
    trace_count: int
    evidence_count: int
    decision_v2: LeaderDecisionV2 | None = None
    needs_clarification:    bool = False
    clarification_question: str | None = None
