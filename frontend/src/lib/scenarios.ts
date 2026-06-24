// scenarios.ts — 골든 데이터셋 시나리오 (Python scenarios.py 와 동기화)

export type ScenarioExpected = {
  intent?: string;
  mustDetectConcepts: string[];
  mustSelectAgents: string[];
  answerMustContain: string[];
  answerMustNotContain: string[];
  minEvidence: number;
};

export type Scenario = {
  id: string;
  category: "intent" | "concept" | "agent" | "answer" | "edge";
  question: string;
  description: string;
  expected: ScenarioExpected;
};

export type ScenarioCategory = Scenario["category"];

export const CATEGORY_LABEL: Record<ScenarioCategory, string> = {
  intent:   "의도 분류",
  concept:  "Concept 탐지",
  agent:    "Agent 선택",
  answer:   "답변 품질",
  edge:     "엣지 케이스",
};

export const SCENARIOS: Scenario[] = [
  // ── INTENT ──────────────────────────────────────────────────
  {
    id: "S001", category: "intent",
    question: "신용대출 금리 알려줘",
    description: "기본 금리 조회 — INQUIRY 의도, RATE_AGENT 실행",
    expected: { intent: "INQUIRY", mustDetectConcepts: ["CONCEPT_INTEREST_RATE"], mustSelectAgents: ["RATE_AGENT"], answerMustContain: ["금리"], answerMustNotContain: ["오류", "알 수 없"], minEvidence: 1 },
  },
  {
    id: "S002", category: "intent",
    question: "개인신용대출 상품에는 어떤 것들이 있나요?",
    description: "상품 목록 조회 — INQUIRY 의도, PRODUCT_AGENT 실행",
    expected: { intent: "INQUIRY", mustDetectConcepts: ["CONCEPT_PERSONAL_CREDIT_LOAN"], mustSelectAgents: ["PRODUCT_AGENT"], answerMustContain: ["대출"], answerMustNotContain: [], minEvidence: 1 },
  },
  {
    id: "S003", category: "intent",
    question: "대출 신청에 필요한 서류가 뭐예요?",
    description: "서류 조회 — INQUIRY 의도, POLICY_AGENT 실행",
    expected: { intent: "INQUIRY", mustDetectConcepts: ["CONCEPT_REQUIRED_DOCUMENT"], mustSelectAgents: ["POLICY_AGENT"], answerMustContain: ["서류"], answerMustNotContain: [], minEvidence: 1 },
  },
  {
    id: "S004", category: "intent",
    question: "대출 약관이나 정책 내용을 알고 싶어요",
    description: "정책/약관 조회 — INQUIRY 의도, POLICY_AGENT 실행",
    expected: { intent: "INQUIRY", mustDetectConcepts: ["CONCEPT_POLICY"], mustSelectAgents: ["POLICY_AGENT"], answerMustContain: ["정책"], answerMustNotContain: [], minEvidence: 1 },
  },
  {
    id: "S005", category: "intent",
    question: "우대금리 조건이 어떻게 돼요?",
    description: "우대금리 조회 — CONCEPT_PREFERENTIAL_RATE 탐지",
    expected: { intent: "INQUIRY", mustDetectConcepts: ["CONCEPT_PREFERENTIAL_RATE"], mustSelectAgents: ["RATE_AGENT"], answerMustContain: ["우대"], answerMustNotContain: [], minEvidence: 1 },
  },
  {
    id: "S006", category: "intent",
    question: "직장인 신용대출과 전세자금대출 금리를 비교해줘",
    description: "금리 비교 — COMPARISON 의도",
    expected: { intent: "COMPARISON", mustDetectConcepts: ["CONCEPT_INTEREST_RATE"], mustSelectAgents: ["RATE_AGENT"], answerMustContain: ["금리"], answerMustNotContain: [], minEvidence: 1 },
  },
  {
    id: "S007", category: "intent",
    question: "A은행과 B은행 신용대출 조건 차이가 뭐야?",
    description: "상품 비교 — COMPARISON 의도",
    expected: { intent: "COMPARISON", mustDetectConcepts: ["CONCEPT_PERSONAL_CREDIT_LOAN"], mustSelectAgents: [], answerMustContain: ["대출"], answerMustNotContain: [], minEvidence: 1 },
  },
  {
    id: "S008", category: "intent",
    question: "신용대출 신청하려면 어떻게 해야 하나요?",
    description: "신청 절차 안내 — APPLICATION 의도",
    expected: { intent: "APPLICATION", mustDetectConcepts: ["CONCEPT_APPLICATION_CONDITION"], mustSelectAgents: [], answerMustContain: ["신청"], answerMustNotContain: [], minEvidence: 1 },
  },
  {
    id: "S009", category: "intent",
    question: "대출 신청 자격 조건이 어떻게 되나요? 직장인인데 가능한가요?",
    description: "자격 조건 확인 — APPLICATION 의도",
    expected: { intent: "APPLICATION", mustDetectConcepts: ["CONCEPT_APPLICATION_CONDITION"], mustSelectAgents: [], answerMustContain: ["조건"], answerMustNotContain: [], minEvidence: 1 },
  },
  {
    id: "S010", category: "intent",
    question: "나한테 맞는 대출 상품 추천해줘",
    description: "상품 추천 — RECOMMENDATION 의도",
    expected: { intent: "RECOMMENDATION", mustDetectConcepts: ["CONCEPT_LOAN_PRODUCT"], mustSelectAgents: ["PRODUCT_AGENT"], answerMustContain: ["상품"], answerMustNotContain: [], minEvidence: 1 },
  },

  // ── CONCEPT ─────────────────────────────────────────────────
  {
    id: "S011", category: "concept",
    question: "신용대출 금리와 필요서류를 함께 알려줘",
    description: "복합 조회 — 금리+서류 2개 Concept",
    expected: { mustDetectConcepts: ["CONCEPT_INTEREST_RATE", "CONCEPT_REQUIRED_DOCUMENT"], mustSelectAgents: ["RATE_AGENT", "POLICY_AGENT"], answerMustContain: ["금리", "서류"], answerMustNotContain: [], minEvidence: 2 },
  },
  {
    id: "S012", category: "concept",
    question: "개인신용대출 조건과 금리 범위를 비교해줘",
    description: "복합 비교 — 대출+금리 Concept",
    expected: { mustDetectConcepts: ["CONCEPT_INTEREST_RATE"], mustSelectAgents: ["RATE_AGENT"], answerMustContain: ["금리"], answerMustNotContain: [], minEvidence: 1 },
  },
  {
    id: "S013", category: "concept",
    question: "대출 신청 전에 유의사항과 필요 서류를 미리 확인하고 싶어요",
    description: "정책+서류 복합 — POLICY_AGENT",
    expected: { mustDetectConcepts: ["CONCEPT_REQUIRED_DOCUMENT"], mustSelectAgents: ["POLICY_AGENT"], answerMustContain: ["서류"], answerMustNotContain: [], minEvidence: 1 },
  },

  // ── AGENT ────────────────────────────────────────────────────
  {
    id: "S014", category: "agent",
    question: "1000만원을 3년 동안 빌리면 월 상환금이 얼마야?",
    description: "상환 시뮬레이션 — 금액/기간 파라미터",
    expected: { mustDetectConcepts: [], mustSelectAgents: ["RATE_AGENT"], answerMustContain: ["월"], answerMustNotContain: ["오류"], minEvidence: 1 },
  },
  {
    id: "S015", category: "agent",
    question: "5000만원 5년 연 4.5% 원리금균등상환 월납입금 계산해줘",
    description: "상세 파라미터 시뮬레이션",
    expected: { mustDetectConcepts: [], mustSelectAgents: ["RATE_AGENT"], answerMustContain: ["월"], answerMustNotContain: [], minEvidence: 1 },
  },

  // ── ANSWER ───────────────────────────────────────────────────
  {
    id: "S016", category: "answer",
    question: "신용대출 금리 알려줘",
    description: "면책 문구 포함 여부 검증",
    expected: { intent: "INQUIRY", mustDetectConcepts: [], mustSelectAgents: [], answerMustContain: ["※ 본 안내는 참고 목적"], answerMustNotContain: [], minEvidence: 1 },
  },
  {
    id: "S017", category: "answer",
    question: "지금 대출 받을 수 있어요? 신용 점수 600점인데",
    description: "민감 정보 질문 — 부적절 내용 미포함",
    expected: { mustDetectConcepts: [], mustSelectAgents: [], answerMustContain: [], answerMustNotContain: ["보장", "확정"], minEvidence: 0 },
  },

  // ── EDGE ─────────────────────────────────────────────────────
  {
    id: "S018", category: "edge",
    question: "오늘 날씨가 어때요?",
    description: "도메인 외 질문 — 500 에러 없이 graceful 응답",
    expected: { mustDetectConcepts: [], mustSelectAgents: [], answerMustContain: [], answerMustNotContain: ["Internal Server Error"], minEvidence: 0 },
  },
  {
    id: "S019", category: "edge",
    question: "ㅇㅇ",
    description: "최소 입력 — 서비스 장애 없이 응답",
    expected: { mustDetectConcepts: [], mustSelectAgents: [], answerMustContain: [], answerMustNotContain: ["Internal Server Error"], minEvidence: 0 },
  },
  {
    id: "S020", category: "edge",
    question: "대출 신청부터 금리 비교, 서류 준비, 약관 확인까지 한 번에 다 알려줘",
    description: "모든 Agent 활성화 시나리오",
    expected: { mustDetectConcepts: ["CONCEPT_INTEREST_RATE"], mustSelectAgents: [], answerMustContain: ["금리"], answerMustNotContain: [], minEvidence: 2 },
  },
];
