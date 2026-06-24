"""
scenarios.py — AI 상담 골든 데이터셋 (20개 시나리오)

각 시나리오는 다음을 정의한다:
  id              : 시나리오 고유 ID
  category        : 테스트 분류 (intent / concept / agent / answer / edge)
  question        : 사용자 입력 메시지
  expected.intent : 기대 의도 (None이면 검증 생략)
  expected.must_detect_concepts  : 반드시 탐지돼야 할 Concept ID 목록
  expected.must_select_agents    : 반드시 선택돼야 할 Agent ID 목록
  expected.answer_must_contain   : 답변에 반드시 포함돼야 할 키워드 목록
  expected.answer_must_not_contain: 답변에 포함되면 안 되는 키워드 목록
  expected.min_evidence          : 최소 Evidence 건수
"""

from dataclasses import dataclass, field


@dataclass
class ScenarioExpected:
    intent: str | None = None
    must_detect_concepts: list[str] = field(default_factory=list)
    must_select_agents: list[str] = field(default_factory=list)
    answer_must_contain: list[str] = field(default_factory=list)
    answer_must_not_contain: list[str] = field(default_factory=list)
    min_evidence: int = 1


@dataclass
class Scenario:
    id: str
    category: str
    question: str
    expected: ScenarioExpected
    description: str = ""


SCENARIOS: list[Scenario] = [

    # ── INQUIRY (단순 조회) ──────────────────────────────────────

    Scenario(
        id="S001",
        category="intent",
        question="신용대출 금리 알려줘",
        description="기본 금리 조회 — INQUIRY 의도, RATE_AGENT 실행",
        expected=ScenarioExpected(
            intent="INQUIRY",
            must_detect_concepts=["CONCEPT_INTEREST_RATE"],
            must_select_agents=["RATE_AGENT"],
            answer_must_contain=["금리"],
            answer_must_not_contain=["오류", "알 수 없"],
            min_evidence=1,
        ),
    ),

    Scenario(
        id="S002",
        category="intent",
        question="개인신용대출 상품에는 어떤 것들이 있나요?",
        description="상품 목록 조회 — INQUIRY 의도, PRODUCT_AGENT 실행",
        expected=ScenarioExpected(
            intent="INQUIRY",
            must_detect_concepts=["CONCEPT_PERSONAL_CREDIT_LOAN"],
            must_select_agents=["PRODUCT_AGENT"],
            answer_must_contain=["대출"],
            min_evidence=1,
        ),
    ),

    Scenario(
        id="S003",
        category="intent",
        question="대출 신청에 필요한 서류가 뭐예요?",
        description="서류 조회 — INQUIRY 의도, POLICY_AGENT 실행 (REQUIRED_DOCUMENT 담당)",
        expected=ScenarioExpected(
            intent="INQUIRY",
            must_detect_concepts=["CONCEPT_REQUIRED_DOCUMENT"],
            must_select_agents=["POLICY_AGENT"],
            answer_must_contain=["서류"],
            min_evidence=1,
        ),
    ),

    Scenario(
        id="S004",
        category="intent",
        question="대출 약관이나 정책 내용을 알고 싶어요",
        description="정책/약관 조회 — INQUIRY 의도, POLICY_AGENT 실행",
        expected=ScenarioExpected(
            intent="INQUIRY",
            must_detect_concepts=["CONCEPT_POLICY"],
            must_select_agents=["POLICY_AGENT"],
            answer_must_contain=["정책"],
            min_evidence=1,
        ),
    ),

    Scenario(
        id="S005",
        category="intent",
        question="우대금리 조건이 어떻게 돼요?",
        description="우대금리 조회 — CONCEPT_PREFERENTIAL_RATE 탐지",
        expected=ScenarioExpected(
            intent="INQUIRY",
            must_detect_concepts=["CONCEPT_PREFERENTIAL_RATE"],
            must_select_agents=["RATE_AGENT"],
            answer_must_contain=["우대"],
            min_evidence=1,
        ),
    ),

    # ── COMPARISON (비교) ───────────────────────────────────────

    Scenario(
        id="S006",
        category="intent",
        question="직장인 신용대출과 전세자금대출 금리를 비교해줘",
        description="금리 비교 — COMPARISON 의도, 복수 Agent",
        expected=ScenarioExpected(
            intent="COMPARISON",
            must_detect_concepts=["CONCEPT_INTEREST_RATE"],
            must_select_agents=["RATE_AGENT"],
            answer_must_contain=["금리"],
            min_evidence=1,
        ),
    ),

    Scenario(
        id="S007",
        category="intent",
        question="A은행과 B은행 신용대출 조건 차이가 뭐야?",
        description="상품 비교 — COMPARISON 의도 (신용대출 키워드로 PERSONAL_CREDIT_LOAN 탐지)",
        expected=ScenarioExpected(
            intent="COMPARISON",
            must_detect_concepts=["CONCEPT_PERSONAL_CREDIT_LOAN"],
            answer_must_contain=["대출"],
            min_evidence=1,
        ),
    ),

    # ── APPLICATION (신청/절차) ─────────────────────────────────

    Scenario(
        id="S008",
        category="intent",
        question="신용대출 신청하려면 어떻게 해야 하나요?",
        description="신청 절차 안내 — APPLICATION 의도",
        expected=ScenarioExpected(
            intent="APPLICATION",
            must_detect_concepts=["CONCEPT_APPLICATION_CONDITION"],
            answer_must_contain=["신청"],
            min_evidence=1,
        ),
    ),

    Scenario(
        id="S009",
        category="intent",
        question="대출 신청 자격 조건이 어떻게 되나요? 직장인인데 가능한가요?",
        description="자격 조건 확인 — APPLICATION 의도, POLICY_AGENT 실행",
        expected=ScenarioExpected(
            intent="APPLICATION",
            must_detect_concepts=["CONCEPT_APPLICATION_CONDITION"],
            answer_must_contain=["조건"],
            min_evidence=1,
        ),
    ),

    # ── RECOMMENDATION (추천) ───────────────────────────────────

    Scenario(
        id="S010",
        category="intent",
        question="나한테 맞는 대출 상품 추천해줘",
        description="상품 추천 — RECOMMENDATION 의도, PRODUCT_AGENT 실행",
        expected=ScenarioExpected(
            intent="RECOMMENDATION",
            must_detect_concepts=["CONCEPT_LOAN_PRODUCT"],
            must_select_agents=["PRODUCT_AGENT"],
            answer_must_contain=["상품"],
            min_evidence=1,
        ),
    ),

    # ── 복합 질문 (Concept 다수) ────────────────────────────────

    Scenario(
        id="S011",
        category="concept",
        question="신용대출 금리와 필요서류를 함께 알려줘",
        description="복합 조회 — 금리+서류 2개 Concept, RATE_AGENT+POLICY_AGENT",
        expected=ScenarioExpected(
            must_detect_concepts=["CONCEPT_INTEREST_RATE", "CONCEPT_REQUIRED_DOCUMENT"],
            must_select_agents=["RATE_AGENT", "POLICY_AGENT"],
            answer_must_contain=["금리", "서류"],
            min_evidence=2,
        ),
    ),

    Scenario(
        id="S012",
        category="concept",
        question="개인신용대출 조건과 금리 범위를 비교해줘",
        description="복합 비교 — 대출+금리 Concept, PRODUCT_AGENT+RATE_AGENT",
        expected=ScenarioExpected(
            must_detect_concepts=["CONCEPT_INTEREST_RATE"],
            must_select_agents=["RATE_AGENT"],
            answer_must_contain=["금리"],
            min_evidence=1,
        ),
    ),

    Scenario(
        id="S013",
        category="concept",
        question="대출 신청 전에 유의사항과 필요 서류를 미리 확인하고 싶어요",
        description="정책+서류 복합 — POLICY_AGENT (REQUIRED_DOCUMENT 담당)",
        expected=ScenarioExpected(
            must_detect_concepts=["CONCEPT_REQUIRED_DOCUMENT"],
            must_select_agents=["POLICY_AGENT"],
            answer_must_contain=["서류"],
            min_evidence=1,
        ),
    ),

    # ── 시뮬레이션 ───────────────────────────────────────────────

    Scenario(
        id="S014",
        category="agent",
        question="1000만원을 3년 동안 빌리면 월 상환금이 얼마야?",
        description="상환 시뮬레이션 — 금액/기간 파라미터 추출 검증",
        expected=ScenarioExpected(
            must_select_agents=["RATE_AGENT"],
            answer_must_contain=["월"],
            answer_must_not_contain=["오류"],
            min_evidence=1,
        ),
    ),

    Scenario(
        id="S015",
        category="agent",
        question="5000만원 5년 연 4.5% 원리금균등상환 월납입금 계산해줘",
        description="상세 파라미터 시뮬레이션 — 금액/기간/금리 모두 추출",
        expected=ScenarioExpected(
            must_select_agents=["RATE_AGENT"],
            answer_must_contain=["월"],
            min_evidence=1,
        ),
    ),

    # ── 답변 품질 ───────────────────────────────────────────────

    Scenario(
        id="S016",
        category="answer",
        question="신용대출 금리 알려줘",
        description="면책 문구 포함 여부 검증 (INQUIRY → ※ 본 안내는 참고 목적)",
        expected=ScenarioExpected(
            intent="INQUIRY",
            answer_must_contain=["※ 본 안내는 참고 목적"],
            min_evidence=1,
        ),
    ),

    Scenario(
        id="S017",
        category="answer",
        question="지금 대출 받을 수 있어요? 신용 점수 600점인데",
        description="민감 정보 포함 질문 — 면책 문구 + 부적절 내용 미포함",
        expected=ScenarioExpected(
            answer_must_not_contain=["보장", "확정"],
            min_evidence=0,
        ),
    ),

    # ── 엣지 케이스 ─────────────────────────────────────────────

    Scenario(
        id="S018",
        category="edge",
        question="오늘 날씨가 어때요?",
        description="도메인 외 질문 — 500 에러 없이 graceful 응답",
        expected=ScenarioExpected(
            answer_must_not_contain=["Internal Server Error"],
            min_evidence=0,
        ),
    ),

    Scenario(
        id="S019",
        category="edge",
        question="ㅇㅇ",
        description="최소 입력 (의미 없는 메시지) — 서비스 장애 없이 응답",
        expected=ScenarioExpected(
            answer_must_not_contain=["Internal Server Error"],
            min_evidence=0,
        ),
    ),

    Scenario(
        id="S020",
        category="edge",
        question="대출 신청부터 금리 비교, 서류 준비, 약관 확인까지 한 번에 다 알려줘",
        description="모든 Agent 활성화 시나리오 — 최대 복합 질문",
        expected=ScenarioExpected(
            must_detect_concepts=["CONCEPT_INTEREST_RATE"],
            answer_must_contain=["금리"],
            min_evidence=2,
        ),
    ),
]
