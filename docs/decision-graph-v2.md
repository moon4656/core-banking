# Decision Graph 개선 설계서 v2.0

> 작성일: 2026-06-14
> 대상 시스템: Core Banking AI Agent (FastAPI + PostgreSQL + Redis + GPT-4o)
> 설계 범위: Leader Agent Decision Graph 개선 — Concept 분류 / Agent 재정의 / Answer Slot Ranking / Memory Save Decision

---

## 목차

1. [현재 Decision Graph 문제점 요약](#1-현재-decision-graph-문제점-요약)
2. [개선 방향 검토 결과](#2-개선-방향-검토-결과)
3. [최종 추천 Decision Graph 구조](#3-최종-추천-decision-graph-구조)
4. [Concept 분류 기준](#4-concept-분류-기준)
5. [Agent 역할 재정의](#5-agent-역할-재정의)
6. [SEARCH_AGENT 처리 방안](#6-search_agent-처리-방안)
7. [Tool 매핑 기준](#7-tool-매핑-기준)
8. [Leader Decision Schema](#8-leader-decision-schema)
9. [Answer Slot Ranking Schema](#9-answer-slot-ranking-schema)
10. [Validation 설계](#10-validation-설계)
11. [Memory Save Decision 설계](#11-memory-save-decision-설계)
12. [UI 개선안](#12-ui-개선안)
13. [Trace / DB 테이블 설계](#13-trace--db-테이블-설계)
14. [개발 Task 목록](#14-개발-task-목록)
15. [MVP 우선순위](#15-mvp-우선순위)
16. [나중에 확장할 항목](#16-나중에-확장할-항목)
17. [리스크 및 주의사항](#17-리스크-및-주의사항)

---

## 1. 현재 Decision Graph 문제점 요약

| # | 문제 | 영향 |
|---|---|---|
| 1 | Concept 7개가 동일 중요도로 처리됨 | Leader가 무엇을 우선해야 할지 판단 기준 없음 |
| 2 | Core/Supporting/Reference 계층 없음 | Agent 선택이 전체 Concept에 끌려다님 |
| 3 | Agent 선택/미선택 근거 Trace 없음 | 운영자가 "왜 이 Agent가 선택됐나" 파악 불가 |
| 4 | SEARCH_AGENT 역할 모호 | 독립 Agent인지 Tool 래퍼인지 불명확 |
| 5 | DOCUMENT_SEARCH 위치 혼재 | POLICY_AGENT 내부인지 독립 Tool인지 불명확 |
| 6 | RATE_LOOKUP vs RATE_SIMULATION 구분 없음 | 개인 조건 없을 때도 시뮬레이션 호출 위험 |
| 7 | Re-ranking이 전체 1위 방식 | 복합 질문에서 항목별 근거 선택 불가 |
| 8 | Memory Save 기준 없음 | 민감 금융정보가 장기 저장될 위험 |
| 9 | Long-term Memory 저장 위험 | 금리조건·대출한도·신용정보 저장 가능성 |
| 10 | Leader 판단 감사 로그 빈약 | AI 설명 가능성(XAI) 요건 미충족 |

---

## 2. 개선 방향 검토 결과

### ✅ 적절한 방향

**Concept Core/Supporting/Reference 분류**
Leader가 선택 우선순위를 결정하는 핵심 근거가 된다. confidence가 동적으로 변할 수 있으므로 threshold를 넘지 못하면 한 단계 강등(Core→Supporting→제외)하는 로직이 필요하다.

**SEARCH_AGENT 기본 미선택 + DOCUMENT_SEARCH → POLICY_AGENT 내부 Tool**
현재 MVP에서 SEARCH_AGENT의 독립적 부가가치가 불명확하다. 대부분의 서류 조회는 POLICY_AGENT로 처리 가능하다.

**RATE_LOOKUP vs RATE_SIMULATION 분리**
필수 개선. 사용자가 개인 조건(소득·신용점수·기간·금액)을 제공했는지 여부로 분기한다.

**POLICY_AGENT가 서류/조건/정책 통합 담당**
논리적 경계가 명확해진다.

**Answer Slot별 Evidence Ranking**
복합 질문에서 항목별 근거 선택은 품질의 핵심이다.

**Memory Save Decision 단계 추가**
금융 상담 AI에서 저장 여부 판단은 별도 단계로 분리해야 한다.

### ⚠️ 조건부 수정 필요

**PRODUCT_AGENT → Product Resolver Tool로 낮추기**
MVP에서는 **경량 Agent로 유지**를 권장한다. Tool로 낮추면 나중에 상품 비교/추천 기능 추가 시 구조 변경이 크다. 대신 단순 식별 시 `role=product_identification`으로 실행하고, Tool은 PRODUCT_RESOLVE 하나만 호출하는 방식으로 경량화한다.

**Re-ranking 전면 교체**
"기존 Re-ranking 제거"가 아니라 "Answer Slot Ranking으로 대체"다. 기존 Evidence 점수 체계(데이터품질 50% + 의도관련도 40% + 속도 10%)는 Evidence 후보 점수 산정에 재활용한다.

---

## 3. 최종 추천 Decision Graph 구조

```
[User Query]
      │
      ▼
┌─────────────────────────────────────┐
│ Context Load                        │
│  ├─ Short Memory (Redis, 5턴)       │
│  └─ Long-term Memory (비민감 요약)  │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│ Intent Analysis                     │
│  출력: intent_name / confidence /   │
│        fallback 여부                │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│ Concept Detection                                       │
│  ┌─ Core (threshold ≥ 0.80)                            │
│  │   PERSONAL_CREDIT_LOAN, INTEREST_RATE,              │
│  │   REQUIRED_DOCUMENT                                 │
│  ├─ Supporting (threshold ≥ 0.65)                      │
│  │   PREFERENTIAL_RATE, APPLICATION_CONDITION          │
│  └─ Reference (threshold ≥ 0.60)                       │
│      LOAN_PRODUCT, POLICY                              │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│ Decision Rule Evaluation            │
│  Core → 필수 Agent 결정            │
│  Supporting → 보조 Tool 결정       │
│  threshold 미달 → 강등 또는 제외   │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ Leader Decision                                             │
│  selected_agents: [PRODUCT_AGENT*, RATE_AGENT,             │
│                    POLICY_AGENT]                            │
│  rejected_agents: [SEARCH_AGENT]                           │
│  execution_strategy: parallel                              │
│  *경량 식별 역할 (PRODUCT_RESOLVE 1회만)                   │
└─────────────────────────────────────────────────────────────┘
      │
      ▼ (병렬)
┌──────────────────┬───────────────────┬────────────────────┐
│ PRODUCT_AGENT    │ RATE_AGENT        │ POLICY_AGENT       │
│ (경량 식별)      │                   │                    │
│ └ PRODUCT_RESOLVE│ ├ RATE_LOOKUP     │ ├ DOCUMENT_SEARCH  │
│                  │ └ RATE_RULE_LOOKUP│ ├ POLICY_LOOKUP    │
│                  │  (RATE_SIMULATION │ └ ELIGIBILITY_CHECK│
│                  │   조건 있을 때만) │   (조건 감지 시)   │
└──────────────────┴───────────────────┴────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│ Evidence Merge                      │
│  각 Tool 결과 → Evidence 수집       │
│  source / score / raw_data 포함     │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│ Answer Slot Ranking                                     │
│  slot: interest_rate  → RATE_LOOKUP > RATE_RULE_LOOKUP │
│  slot: required_doc   → DOCUMENT_SEARCH > POLICY_LOOKUP│
│  slot: preferential   → RATE_RULE_LOOKUP (supporting)  │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│ Validation                                              │
│  최신성 / 정책버전 / 금리유효일 / 개인정보              │
│  환각위험 / 답변범위 / 면책안내 필요 여부               │
└─────────────────────────────────────────────────────────┘
      │ (실패 시 → 경고 플래그 + fallback 응답)
      ▼
┌─────────────────────────────────────┐
│ Final Answer Generation             │
│  Slot별 선택 Evidence 기반 생성     │
│  면책/상담 안내 문구 자동 삽입      │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│ Memory Save Decision                                    │
│  저장 가치 / 민감정보 여부 / 마스킹 / 동의 필요성      │
└─────────────────────────────────────────────────────────┘
      │              │
      ▼              ▼
[Short Memory]  [Long-term Memory]
(대화 연속성)   (비민감 요약만)
```

### 노드별 상세

| 노드 | 목적 | 입력 | 출력 | Trace 저장 | 실패 fallback |
|---|---|---|---|---|---|
| Context Load | 이전 대화 복원 | session_id | short_memory, long_term_summary | ai_trace_event | 메모리 없이 계속 |
| Intent Analysis | 질문 의도 분류 | user_query + context | intent_name, confidence | ai_decision_trace | UNKNOWN_INTENT → 일반 안내 |
| Concept Detection | 관련 개념 감지 | intent + query | Core/Supporting/Reference Concept 목록 | ai_concept_detection | Concept 없으면 UNKNOWN_INTENT fallback |
| Decision Rule Evaluation | Agent 선택 규칙 적용 | classified_concepts | triggered_rules, required/optional agents | ai_decision_trace | 규칙 미충족 → UNKNOWN_INTENT fallback |
| Leader Decision | 최종 Agent 선택 결정 | rules + concepts | selected/rejected agents, execution_strategy | ai_agent_selection | executor.py fallback |
| Agent Execution | Agent 병렬 실행 | selected_agents, product_id | 각 Agent 결과 | ai_tool_execution | Agent 실패 → partial 결과 |
| Evidence Merge | Tool 결과 통합 | 모든 Tool 결과 | List[Evidence] | ai_evidence_trace | 일부 Evidence 없이 계속 |
| Answer Slot Ranking | 항목별 최적 근거 선택 | evidences + slots | AnswerSlotRanking | ai_answer_slot_ranking | 슬롯 미해결 → 해당 항목 생략 |
| Validation | 답변 품질/안전 검증 | ranked_evidences | ValidationResult, risk_flags | ai_validation_trace | 경고 플래그 + 면책 문구 삽입 |
| Final Answer | 최종 답변 생성 | slots + evidences + validation | final_answer_text | ai_final_answer_trace | 템플릿 기반 fallback 답변 |
| Memory Save Decision | 저장 여부 판단 | final_answer + validation | MemorySaveDecision | ai_memory_save_decision | 저장 불가 시 skip |

---

## 4. Concept 분류 기준

### Core Concepts — confidence threshold ≥ 0.80

| Concept | 연결 Agent | 연결 Tool | 선택 근거 | 미선택/강등 기준 |
|---|---|---|---|---|
| **PERSONAL_CREDIT_LOAN** | PRODUCT_AGENT, RATE_AGENT, POLICY_AGENT | PRODUCT_RESOLVE | 개인신용대출 상담 맥락의 기본 도메인 | confidence < 0.80 → Reference로 강등 |
| **INTEREST_RATE** | RATE_AGENT | RATE_LOOKUP, RATE_RULE_LOOKUP | "금리" 키워드 직접 포함 | confidence < 0.80 → Supporting으로 강등 |
| **REQUIRED_DOCUMENT** | POLICY_AGENT | DOCUMENT_SEARCH, POLICY_LOOKUP | "서류" 키워드 직접 포함 | confidence < 0.80 → Supporting으로 강등 |

### Supporting Concepts — confidence threshold ≥ 0.65

| Concept | 연결 Agent | 연결 Tool | 선택 근거 | 미선택 기준 |
|---|---|---|---|---|
| **PREFERENTIAL_RATE** | RATE_AGENT | RATE_RULE_LOOKUP | 금리 질의 시 우대금리 가능성 탐지 | confidence < 0.65 → 제외 |
| **APPLICATION_CONDITION** | POLICY_AGENT | ELIGIBILITY_CHECK | 서류/신청 질의 시 조건 검증 필요 | confidence < 0.65 → 제외 |

### Reference Concepts — confidence threshold ≥ 0.60 (참고용, 독립 Agent 미트리거)

| Concept | 연결 Agent | 연결 Tool | 선택 근거 | 처리 방식 |
|---|---|---|---|---|
| **LOAN_PRODUCT** | PRODUCT_AGENT (경량) | PRODUCT_RESOLVE | 대출 도메인 맥락 설정 | PRODUCT_RESOLVE 1회만 경량 호출 |
| **POLICY** | POLICY_AGENT | POLICY_LOOKUP | 정책 문서 근거 보강 | POLICY_LOOKUP을 supporting Evidence로만 활용 |

### 강등 로직

```
if INTEREST_RATE.confidence >= 0.80  → Core     → RATE_AGENT 필수 선택
if 0.65 <= confidence < 0.80         → Supporting → RATE_AGENT 선택, RATE_RULE_LOOKUP 생략 가능
if confidence < 0.65                 → 제외
```

---

## 5. Agent 역할 재정의

### PRODUCT_AGENT — 상품 식별 전담 (추천/비교 제외)

| 항목 | 내용 |
|---|---|
| 선택 조건 | PERSONAL_CREDIT_LOAN ≥ 0.85 또는 LOAN_PRODUCT Reference 감지 |
| 단순 식별 시 Agent 유지 | Yes — 경량 실행 (`role=product_identification`, PRODUCT_RESOLVE 1회) |
| Tool로 낮추지 않는 이유 | 추후 상품 비교/추천 기능 추가 시 구조 변경 비용 최소화 |
| 상품 추천 질문 처리 | MVP 제외. 감지 시 "상담원 연결 안내" fallback |
| 단순 식별 vs 추천 구분 | "XX 대출 서류가 뭐야?" → 식별만 / "A와 B 중 뭐가 나아?" → 추천 → 제외 |

### RATE_AGENT — 금리 조회 및 시뮬레이션

| 항목 | 내용 |
|---|---|
| INTEREST_RATE 처리 | RATE_LOOKUP (기본) + RATE_RULE_LOOKUP (우대, PREFERENTIAL_RATE 감지 시) |
| PREFERENTIAL_RATE 처리 | RATE_RULE_LOOKUP만 추가 호출 (RATE_AGENT 재사용) |
| RATE_LOOKUP 조건 | 사용자 개인 조건 미제공 — "금리가 얼마야?" |
| RATE_SIMULATION 조건 | 소득·신용점수·대출기간·금액 중 하나라도 제공 시 |
| 현재 질문 "금리와 서류 알려줘" | RATE_LOOKUP + RATE_RULE_LOOKUP (시뮬레이션 조건 없음) |

**RATE_LOOKUP vs RATE_SIMULATION 비교**

| 구분 | RATE_LOOKUP | RATE_SIMULATION |
|---|---|---|
| 사용 조건 | 개인 조건 미제공 | 소득/신용점수/기간/금액 중 1개 이상 제공 |
| 입력 | product_id, loan_type | income, credit_score, loan_amount, term_months |
| 출력 | 공시 금리 범위 | 예상 개인 금리 + 월 상환액 |
| fallback | 금리 조회 불가 안내 | RATE_LOOKUP으로 자동 대체 |

### POLICY_AGENT — 서류·조건·정책·규정 통합

| 항목 | 내용 |
|---|---|
| 처리 Concept | REQUIRED_DOCUMENT(Core), APPLICATION_CONDITION(Supporting), POLICY(Reference) |
| DOCUMENT_SEARCH | 필요서류 목록 — REQUIRED_DOCUMENT Core 감지 시 필수 호출 |
| POLICY_LOOKUP | 정책 근거 보강 — POLICY Reference 감지 또는 서류 근거 보강 필요 시 |
| ELIGIBILITY_CHECK | 신청 자격 — APPLICATION_CONDITION Supporting 감지 시만 호출 |
| 정책 근거 연결 방식 | DOCUMENT_SEARCH 결과에 `policy_ref` 필드로 POLICY_LOOKUP 결과 연결 |

### SEARCH_AGENT — 기본 미선택, 조건부 활성화

| 선택 조건 | 예시 질문 |
|---|---|
| 과거 상담 이력 조회 | "저번에 상담받은 내용 다시 알려줘" |
| 비정형 다중 문서 교차 검색 | "우대금리 관련 규정 문서 전체 찾아줘" |
| POLICY_AGENT 실패 후 retry | POLICY_AGENT 실행 실패 시 자동 선택 |

**현재 질문 "대출 금리와 서류 알려줘" → 미선택** (POLICY_AGENT의 DOCUMENT_SEARCH로 처리)

### Agent 역할 경계 요약표

| Agent | 주요 역할 | 핵심 Tool | 선택 조건 | 미선택 조건 | MVP 빈도 |
|---|---|---|---|---|---|
| PRODUCT_AGENT | 상품 식별 | PRODUCT_RESOLVE | LOAN_PRODUCT/PERSONAL_CREDIT_LOAN 감지 | 상품 언급 없음 | 대부분 경량 실행 |
| RATE_AGENT | 금리 조회/시뮬레이션 | RATE_LOOKUP, RATE_RULE_LOOKUP, RATE_SIMULATION | INTEREST_RATE 감지 | 금리 질문 없음 | 금리 질문 시 필수 |
| POLICY_AGENT | 서류/조건/정책 | DOCUMENT_SEARCH, POLICY_LOOKUP, ELIGIBILITY_CHECK | REQUIRED_DOCUMENT/APPLICATION_CONDITION/POLICY 감지 | 정책/서류 질문 없음 | 서류 질문 시 필수 |
| SEARCH_AGENT | 비정형 검색/이력 조회 | DOCUMENT_SEARCH(광범위) | 상담이력 조회, 비정형 검색 | **기본 미선택** | 드물게 선택 |

---

## 6. SEARCH_AGENT 처리 방안

**결론: 독립 Agent로 유지, 기본 미선택**

```
SEARCH_AGENT 선택 결정 트리:

사용자 질문이 있다
      │
      ├─ "이전 상담" / "상담이력" 키워드 있음? ─→ YES → SEARCH_AGENT 선택
      │
      ├─ POLICY_AGENT 실행 실패 후 retry?    ─→ YES → SEARCH_AGENT 선택
      │
      ├─ 비정형 서류 검색어
      │  (규정 전체, 관련 문서 모두 등)?     ─→ YES → SEARCH_AGENT 선택
      │
      └─ 위 조건 모두 아님 ─→ SEARCH_AGENT 미선택
                              (POLICY_AGENT 내부 Tool 사용)
```

이유:
1. DOCUMENT_SEARCH Tool은 POLICY_AGENT 내부에 포함하여 일반 서류 조회 처리
2. SEARCH_AGENT는 "고급 검색 전문 Agent"로 포지셔닝
3. MVP에서는 거의 미선택되므로 구현 복잡도 낮음

---

## 7. Tool 매핑 기준

### PRODUCT_RESOLVE

| 항목 | 내용 |
|---|---|
| 목적 | 상품 키워드 → 상품 메타데이터 변환 |
| 호출 주체 | PRODUCT_AGENT |
| 호출 조건 | LOAN_PRODUCT 또는 PERSONAL_CREDIT_LOAN 감지 |
| 입력 | `{ "product_keyword": "개인신용대출" }` |
| 출력 | `{ "product_id": "P001", "product_name": "...", "product_type": "personal_credit" }` |
| 최종 답변 사용 | 간접 (다른 Tool 파라미터로 전달) |
| 실패 fallback | product_id=null, 다른 Tool이 기본값으로 실행 |
| UI 표시 | "상품 식별: 개인신용대출 (P001)" |

### RATE_LOOKUP

| 항목 | 내용 |
|---|---|
| 목적 | 공시 기본 금리 조회 (개인 조건 불필요) |
| 호출 주체 | RATE_AGENT |
| 호출 조건 | INTEREST_RATE Core 감지, 사용자 개인 조건 미제공 |
| 입력 | `{ "product_id": "P001", "loan_type": "personal_credit" }` |
| 출력 | `{ "base_rate": 5.2, "min_rate": 3.8, "max_rate": 8.5, "reference_date": "2026-06-14" }` |
| 최종 답변 사용 | Yes — Answer Slot: `interest_rate` (primary) |
| 실패 fallback | "현재 금리 정보를 조회할 수 없습니다" 안내 |
| UI 표시 | "기본 금리: 연 3.8% ~ 8.5% (기준일: 2026-06-14)" |

### RATE_RULE_LOOKUP

| 항목 | 내용 |
|---|---|
| 목적 | 우대금리 조건 목록 조회 |
| 호출 주체 | RATE_AGENT |
| 호출 조건 | PREFERENTIAL_RATE Supporting 감지 시 (RATE_LOOKUP과 병행) |
| 입력 | `{ "product_id": "P001" }` |
| 출력 | `{ "rules": [{"condition": "급여이체", "discount_rate": -0.3}, {"condition": "자동이체", "discount_rate": -0.1}] }` |
| 최종 답변 사용 | Yes — Answer Slot: `interest_rate` (supporting) |
| 실패 fallback | 우대금리 항목 생략, 기본 금리만 안내 |
| UI 표시 | "우대금리: 급여이체 -0.3%p 외 N건" |

### RATE_SIMULATION

| 항목 | 내용 |
|---|---|
| 목적 | 개인 조건 기반 금리 및 상환액 계산 |
| 호출 주체 | RATE_AGENT |
| 호출 조건 | 사용자가 소득·신용점수·대출금액·기간 중 1개 이상 제공 시 |
| 입력 | `{ "income": 5000000, "credit_score": 750, "loan_amount": 30000000, "term_months": 36 }` |
| 출력 | `{ "estimated_rate": 4.5, "monthly_payment": 900000, "total_interest": 450000, "disclaimer": "예상치" }` |
| 최종 답변 사용 | Yes — 개인 조건 제공 시 RATE_LOOKUP 대체 |
| 실패 fallback | RATE_LOOKUP으로 자동 대체 |
| UI 표시 | "시뮬레이션: 예상 금리 4.5%, 월 상환 900,000원" |

### DOCUMENT_SEARCH

| 항목 | 내용 |
|---|---|
| 목적 | 필요서류 목록 조회 |
| 호출 주체 | POLICY_AGENT |
| 호출 조건 | REQUIRED_DOCUMENT Core 감지 시 |
| 입력 | `{ "loan_type": "personal_credit", "applicant_type": "employed" }` |
| 출력 | `{ "documents": ["신분증", "재직증명서", "소득확인서"], "policy_ref": "DOC-2026-003", "valid_date": "2026-06-14" }` |
| 최종 답변 사용 | Yes — Answer Slot: `required_document` (primary) |
| 실패 fallback | 정형 서류 목록 텍스트 안내 |
| UI 표시 | "필요서류: 3건 (정책번호: DOC-2026-003)" |

### POLICY_LOOKUP

| 항목 | 내용 |
|---|---|
| 목적 | 정책/규정 근거 문서 조회 |
| 호출 주체 | POLICY_AGENT |
| 호출 조건 | POLICY Reference 감지 또는 DOCUMENT_SEARCH 결과 근거 보강 필요 시 |
| 입력 | `{ "policy_type": "required_document", "product_id": "P001" }` |
| 출력 | `{ "policy_id": "POL-2026-003", "title": "개인신용대출 필요서류 규정", "version": "v3.1", "effective_date": "2026-01-01" }` |
| 최종 답변 사용 | Supporting (출처 근거, 직접 답변 아님) |
| 실패 fallback | 정책 근거 없이 서류 목록만 제공 |
| UI 표시 | "정책 근거: POL-2026-003 (v3.1, 2026-01-01 시행)" |

### ELIGIBILITY_CHECK

| 항목 | 내용 |
|---|---|
| 목적 | 신청 자격 조건 목록 조회 |
| 호출 주체 | POLICY_AGENT |
| 호출 조건 | APPLICATION_CONDITION Supporting 감지 시만 호출 |
| 입력 | `{ "product_id": "P001" }` |
| 출력 | `{ "conditions": ["만 19세 이상", "소득 있는 자", "신용불량자 제외"], "personal_check_result": null }` |
| 최종 답변 사용 | Yes — Answer Slot: `application_condition` (있을 때) |
| 실패 fallback | "신청조건은 영업점 상담원에게 문의 안내" |
| UI 표시 | "신청조건: 3개 항목 확인됨" |

---

## 8. Leader Decision Schema

```json
{
  "request_id": "req_20260614_abc123",
  "session_id": "sess_xyz789",
  "schema_version": "v2.0",
  "created_at": "2026-06-14T12:00:00Z",

  "user_query": "대출 금리와 서류 알려줘",
  "user_query_masked": "대출 금리와 서류 알려줘",

  "context_loaded": {
    "short_memory_turns": 0,
    "long_term_summary": null,
    "context_applied": false
  },

  "intent": {
    "name": "compound_inquiry",
    "confidence": 0.96,
    "reason": "금리(INTEREST_RATE)와 필요서류(REQUIRED_DOCUMENT) 두 항목을 동시에 질의함",
    "fallback_triggered": false,
    "fallback_reason": null
  },

  "concepts": {
    "core": [
      {
        "name": "PERSONAL_CREDIT_LOAN",
        "confidence": 0.94,
        "threshold": 0.80,
        "reason": "개인신용대출 상담 맥락으로 판단됨",
        "promoted_from": null,
        "demoted_from": null
      },
      {
        "name": "INTEREST_RATE",
        "confidence": 0.91,
        "threshold": 0.80,
        "reason": "금리 문의 키워드 직접 포함",
        "promoted_from": null,
        "demoted_from": null
      },
      {
        "name": "REQUIRED_DOCUMENT",
        "confidence": 0.89,
        "threshold": 0.80,
        "reason": "서류 문의 키워드 직접 포함",
        "promoted_from": null,
        "demoted_from": null
      }
    ],
    "supporting": [
      {
        "name": "PREFERENTIAL_RATE",
        "confidence": 0.74,
        "threshold": 0.65,
        "reason": "금리 질의에서 우대금리 가능성 탐지",
        "promoted_from": null,
        "demoted_from": null
      },
      {
        "name": "APPLICATION_CONDITION",
        "confidence": 0.71,
        "threshold": 0.65,
        "reason": "서류 질의와 연관된 신청조건 검증 가능성",
        "promoted_from": null,
        "demoted_from": null
      }
    ],
    "reference": [
      {
        "name": "LOAN_PRODUCT",
        "confidence": 0.82,
        "threshold": 0.60,
        "reason": "대출 도메인 맥락 설정",
        "promoted_from": null,
        "demoted_from": "core"
      },
      {
        "name": "POLICY",
        "confidence": 0.68,
        "threshold": 0.60,
        "reason": "정책 문서 근거 참고",
        "promoted_from": null,
        "demoted_from": null
      }
    ]
  },

  "decision_rules_applied": [
    {
      "rule_id": "R001",
      "rule_name": "INTEREST_RATE Core → RATE_AGENT 필수 선택",
      "triggered": true
    },
    {
      "rule_id": "R002",
      "rule_name": "REQUIRED_DOCUMENT Core → POLICY_AGENT 필수 선택",
      "triggered": true
    },
    {
      "rule_id": "R003",
      "rule_name": "PREFERENTIAL_RATE Supporting → RATE_RULE_LOOKUP 추가",
      "triggered": true
    },
    {
      "rule_id": "R004",
      "rule_name": "개인 조건 미제공 → RATE_SIMULATION 미호출",
      "triggered": true
    },
    {
      "rule_id": "R005",
      "rule_name": "SEARCH_AGENT 기본 미선택 정책",
      "triggered": true
    }
  ],

  "selected_agents": [
    {
      "agent_name": "PRODUCT_AGENT",
      "role": "product_identification",
      "score": 0.72,
      "reason": "LOAN_PRODUCT Reference 감지 — 상품 메타데이터 식별 필요",
      "execution_mode": "lightweight",
      "tools": ["PRODUCT_RESOLVE"],
      "depends_on": []
    },
    {
      "agent_name": "RATE_AGENT",
      "role": "rate_lookup",
      "score": 0.91,
      "reason": "INTEREST_RATE Core + PREFERENTIAL_RATE Supporting 감지",
      "execution_mode": "normal",
      "tools": ["RATE_LOOKUP", "RATE_RULE_LOOKUP"],
      "depends_on": ["PRODUCT_AGENT"]
    },
    {
      "agent_name": "POLICY_AGENT",
      "role": "document_and_policy_check",
      "score": 0.89,
      "reason": "REQUIRED_DOCUMENT Core + APPLICATION_CONDITION Supporting 감지",
      "execution_mode": "normal",
      "tools": ["DOCUMENT_SEARCH", "POLICY_LOOKUP", "ELIGIBILITY_CHECK"],
      "depends_on": ["PRODUCT_AGENT"]
    }
  ],

  "rejected_agents": [
    {
      "agent_name": "SEARCH_AGENT",
      "score": 0.41,
      "reason": "DOCUMENT_SEARCH는 POLICY_AGENT 내부 Tool로 처리 가능. 상담이력 조회나 비정형 검색 조건 미충족."
    }
  ],

  "execution_strategy": "parallel",
  "parallelization_groups": [
    ["RATE_AGENT", "POLICY_AGENT"]
  ],
  "serial_prerequisite": ["PRODUCT_AGENT"],

  "estimated_execution_ms": 2500,
  "decision_reason": "금리(INTEREST_RATE)와 필요서류(REQUIRED_DOCUMENT)를 동시에 묻는 복합 질문. RATE_AGENT와 POLICY_AGENT를 병렬 실행하되 PRODUCT_AGENT의 상품 식별 결과를 선행 의존성으로 설정한다."
}
```

---

## 9. Answer Slot Ranking Schema

### 설계 원칙

| 원칙 | 내용 |
|---|---|
| Slot 분리 기준 | Intent Analysis 단계에서 질문 항목 추출. 복합 질문은 여러 슬롯으로 분리. |
| Evidence 후보 수집 | 각 슬롯의 intent_keyword와 매핑되는 모든 Tool 결과를 후보로 수집. |
| Ranking 점수 산정 | 데이터 품질(50%) + 슬롯 관련도(40%) + 응답속도 보너스(10%) |
| 최종 Evidence 선택 | 슬롯별 최고 점수 Evidence 선택, 동점 시 latency 낮은 것 우선. |
| 최종 답변 연결 | 각 슬롯에 selected_evidence.evidence_id 연결, LLM 답변 생성 시 해당 Evidence만 입력 제공. |

```json
{
  "request_id": "req_20260614_abc123",
  "answer_slots": [
    {
      "slot_id": "slot_001",
      "slot": "interest_rate",
      "question_part": "금리",
      "slot_keywords": ["금리", "이자", "이율"],
      "answer_required": true,
      "candidate_evidences": [
        {
          "evidence_id": "evd_001",
          "source_tool": "RATE_LOOKUP",
          "source_agent": "RATE_AGENT",
          "data_quality_score": 0.95,
          "slot_relevance_score": 0.97,
          "latency_bonus": 0.08,
          "final_score": 0.94,
          "reason": "기본 금리 질의와 직접 일치, 최신 공시 금리 포함"
        },
        {
          "evidence_id": "evd_002",
          "source_tool": "RATE_RULE_LOOKUP",
          "source_agent": "RATE_AGENT",
          "data_quality_score": 0.88,
          "slot_relevance_score": 0.82,
          "latency_bonus": 0.06,
          "final_score": 0.86,
          "reason": "우대금리 조건 포함 — 기본 금리 보완 정보"
        }
      ],
      "selected_evidence_id": "evd_001",
      "supporting_evidence_ids": ["evd_002"],
      "selection_reason": "기본 금리 안내는 RATE_LOOKUP이 가장 직접적. 우대금리는 보조 근거로 병기."
    },
    {
      "slot_id": "slot_002",
      "slot": "required_document",
      "question_part": "서류",
      "slot_keywords": ["서류", "필요서류", "구비서류", "서류 목록"],
      "answer_required": true,
      "candidate_evidences": [
        {
          "evidence_id": "evd_003",
          "source_tool": "DOCUMENT_SEARCH",
          "source_agent": "POLICY_AGENT",
          "data_quality_score": 0.93,
          "slot_relevance_score": 0.96,
          "latency_bonus": 0.07,
          "final_score": 0.93,
          "reason": "필요서류 목록 직접 조회, 정책 참조번호 포함"
        },
        {
          "evidence_id": "evd_004",
          "source_tool": "POLICY_LOOKUP",
          "source_agent": "POLICY_AGENT",
          "data_quality_score": 0.85,
          "slot_relevance_score": 0.79,
          "latency_bonus": 0.05,
          "final_score": 0.83,
          "reason": "정책/규정 근거 제공 — 서류 목록의 법적 출처"
        }
      ],
      "selected_evidence_id": "evd_003",
      "supporting_evidence_ids": ["evd_004"],
      "selection_reason": "서류 목록 안내는 DOCUMENT_SEARCH가 가장 구체적. POLICY_LOOKUP은 출처 근거로 병기."
    },
    {
      "slot_id": "slot_003",
      "slot": "preferential_rate",
      "question_part": null,
      "slot_keywords": ["우대금리", "할인"],
      "answer_required": false,
      "candidate_evidences": [
        {
          "evidence_id": "evd_002",
          "source_tool": "RATE_RULE_LOOKUP",
          "source_agent": "RATE_AGENT",
          "data_quality_score": 0.88,
          "slot_relevance_score": 0.90,
          "latency_bonus": 0.06,
          "final_score": 0.89,
          "reason": "우대금리 조건 목록 포함"
        }
      ],
      "selected_evidence_id": "evd_002",
      "supporting_evidence_ids": [],
      "selection_reason": "우대금리 조건을 보조 정보로 제공. 사용자가 직접 질문하지 않았으므로 간략 안내."
    }
  ],
  "unresolved_slots": [],
  "total_slots": 3,
  "required_slots_resolved": 2
}
```

---

## 10. Validation 설계

| 검증 항목 | 목적 | 검증 방법 | 실패 시 처리 | UI 표시 | Trace 저장 |
|---|---|---|---|---|---|
| **최신성** | 오래된 데이터 제공 방지 | `valid_date` vs 오늘 날짜 비교 (30일 초과 시 경고) | 경고 플래그 + "최신 정보 확인 필요" 문구 | ⚠️ 최신성 경고 | Yes |
| **정책 버전** | 구버전 정책 기반 답변 방지 | `policy_version` vs DB 최신 버전 비교 | 최신 버전으로 재조회, 실패 시 "정책 변경 가능" 안내 | ⚠️ 버전 불일치 | Yes |
| **금리 유효일** | 만료 금리 정보 제공 방지 | `reference_date` 유효 여부 검증 (7일 이내) | RATE_LOOKUP 재호출, 실패 시 "금리 변동 가능" 안내 | ⚠️ 금리 유효일 경고 | Yes |
| **사용자 권한** | 미인가 정보 노출 방지 | 사용자 role과 답변 데이터 접근 레벨 비교 | 해당 항목 답변 블록, "권한 없음" 안내 | 🔒 권한 제한 | Yes |
| **문서 접근 권한** | 기밀 정책 문서 노출 방지 | 정책 문서 `access_level` vs 사용자 role 비교 | 문서 내용 생략, 제목만 안내 | 🔒 접근 제한 | Yes |
| **출처 신뢰도** | 저신뢰 Evidence 기반 답변 방지 | Evidence final_score < 0.70 이면 경고 | 신뢰도 낮음 플래그, "상담원 확인 권장" 문구 | ⚠️ 신뢰도 낮음 | Yes |
| **환각 위험** | LLM 생성 텍스트의 출처 없는 수치 방지 | 답변 수치를 Evidence 수치와 비교, 불일치 탐지 | 해당 수치 제거 또는 "정확한 수치는 창구 확인" 대체 | ⚠️ 수치 불일치 | Yes |
| **개인정보/민감정보** | 주민번호·계좌번호·신용점수 노출 방지 | 정규식 패턴 매칭 | 해당 필드 `***` 마스킹 후 답변 포함 | 🔒 마스킹 처리 | Yes (마스킹 후) |
| **답변 가능 범위** | 실제 대출 승인 등 업무 범위 초과 방지 | intent가 personal_loan_approval 등이면 거부 | "해당 내용은 영업점/앱에서 확인" fallback | ℹ️ 범위 초과 | Yes |
| **면책 안내 필요** | 금융 상담 AI 법적 책임 제한 | 금리·서류·조건 등 법적 영향 있는 답변 시 | 답변 말미에 면책 안내 자동 삽입 | ℹ️ 면책 안내 포함 | Yes |

---

## 11. Memory Save Decision 설계

### 저장 판단 흐름

```
[Final Answer 완료]
      │
      ▼
[저장 가치 있는 대화인가?]
  - 사용자 질문이 의미있는 정보를 포함하는가?
  - 답변이 정상 생성됐는가?
  - fallback-only 답변이면 → Short Memory만 저장, Long-term 제외
      │
      ▼
[민감정보 포함 여부 스캔]
  - 주민번호, 계좌번호, 신용점수, 소득, 직장명, 대출한도 감지
  - 감지 시 → 해당 항목 마스킹 후 저장
      │
      ▼
[Short Memory Save 판단]
  - 항상 저장 (대화 연속성 필요)
  - 민감정보: 마스킹 후 저장
  - TTL: 1시간
      │
      ▼
[Long-term Memory Save 판단]
  - 저장 가치 기준 충족 여부 확인
  - 민감정보 포함 시 → 저장 불가
  - 기본값: 저장 안 함
```

### Short Memory / Long-term Memory 저장 기준 표

| 항목 | Short Memory | Long-term Memory | 비고 |
|---|---|---|---|
| 사용자 질문 원문 | ✅ 저장 | ❌ 저장 안 함 | 장기 보관 불필요 |
| 의도(intent) | ✅ 저장 | ✅ 저장 (익명화) | "이전에 금리 문의했음" 수준 |
| 선택 Agent 목록 | ✅ 저장 | ❌ 저장 안 함 | 운영 정보 |
| 금리 정보 (공시) | ✅ 저장 | ❌ 저장 안 함 | 시간이 지나면 무의미 |
| 필요서류 목록 | ✅ 저장 | ❌ 저장 안 함 | 정책 변경 가능 |
| 답변 요약 (비민감) | ✅ 저장 | ✅ 저장 | "금리/서류 안내 완료" 수준 |
| 대화 연속성 맥락 | ✅ 저장 | ✅ 저장 (요약) | "3회 이상 문의한 사용자" 등 |
| 주민등록번호 | ❌ 절대 금지 | ❌ 절대 금지 | 저장 절대 불가 |
| 계좌번호 | ❌ 절대 금지 | ❌ 절대 금지 | 저장 절대 불가 |
| 신용점수 | ❌ 절대 금지 | ❌ 절대 금지 | 저장 절대 불가 |
| 소득 정보 | ❌ 절대 금지 | ❌ 절대 금지 | 저장 절대 불가 |
| 직장명 | ❌ 절대 금지 | ❌ 절대 금지 | 저장 절대 불가 |
| 대출 한도/조건 | ❌ 절대 금지 | ❌ 절대 금지 | 저장 절대 불가 |
| 개인 금융 상태 | ❌ 절대 금지 | ❌ 절대 금지 | 저장 절대 불가 |
| 민감한 상담 내용 | 마스킹 후 저장 | ❌ 저장 안 함 | 마스킹 필수 |

### Memory Save Decision Trace 예시

```json
{
  "request_id": "req_20260614_abc123",
  "save_decision": {
    "short_memory": {
      "should_save": true,
      "reason": "정상 응답 완료, 대화 연속성 필요",
      "masking_applied": false,
      "ttl_seconds": 3600
    },
    "long_term_memory": {
      "should_save": true,
      "reason": "금리/서류 복합 문의 패턴 기록 (비민감)",
      "save_content": "사용자가 개인신용대출 금리 및 필요서류를 문의함. 정상 안내 완료.",
      "sensitive_data_detected": false,
      "user_consent_required": false,
      "masking_applied": false,
      "ttl_days": 90,
      "delete_policy": "TTL 만료 후 자동 삭제"
    }
  }
}
```

---

## 12. UI 개선안

### Summary View

| 항목 | 표시 방식 | 예시 |
|---|---|---|
| 사용자 질문 | 텍스트 박스 | "대출 금리와 서류 알려줘" |
| 최종 Intent | 배지 + confidence | `compound_inquiry (96%)` |
| 선택 Agent | 녹색 배지 목록 | `PRODUCT_AGENT` `RATE_AGENT` `POLICY_AGENT` |
| 미선택 Agent | 회색 배지 + hover 사유 | `SEARCH_AGENT` |
| 실행 Tool | 아이콘 목록 | PRODUCT_RESOLVE / RATE_LOOKUP / RATE_RULE_LOOKUP / DOCUMENT_SEARCH / POLICY_LOOKUP |
| 최종 상태 | 색상 상태 아이콘 | ✅ 성공 / ⚠️ 경고 / ❌ 실패 |
| 총 처리 시간 | ms 단위 | `2,340ms` |
| 위험 플래그 | 적색 배지 | `⚠️ 최신성 경고` `🔒 면책 안내 포함` |

### Decision Trace View

| 항목 | 표시 방식 |
|---|---|
| Core Concept | 파란색 배지 + confidence bar |
| Supporting Concept | 주황색 배지 + confidence bar |
| Reference Concept | 회색 배지 + confidence bar |
| threshold 미달로 강등된 Concept | 취소선 + 강등 사유 |
| Concept → Agent 매핑 | 화살표 그래프 |
| Agent 선택 사유 | 펼침 패널 (rule_id + 사유 텍스트) |
| Agent 미선택 사유 | 회색 패널 + 사유 텍스트 |
| 실행 전략 | `병렬 실행` / `순차 실행` 배지 |

### Evidence / Tool View

| 항목 | 표시 방식 |
|---|---|
| Tool 이름 | 텍스트 |
| 호출 Agent | 작은 배지 |
| 입력 요약 | JSON 접힘/펼침 |
| 출력 요약 | JSON 접힘/펼침 |
| latency_ms | 숫자 + 바 차트 (상대적 비교) |
| 성공/실패 | ✅ / ❌ 아이콘 |
| 최종 답변 사용 여부 | `Primary` / `Supporting` / `미사용` 배지 |
| Evidence ID | 링크 (클릭 시 상세) |
| Answer Slot 연결 | `→ interest_rate slot` 배지 |

### 그래프 시각화 색상 기준

| 요소 | 색상 | 색상 코드 |
|---|---|---|
| Core Concept | 파란색 | `#2563EB` |
| Supporting Concept | 주황색 | `#D97706` |
| Reference Concept | 회색 | `#6B7280` |
| 강등된 Concept | 연회색 + 취소선 | `#D1D5DB` |
| 선택 Agent | 녹색 | `#059669` |
| 미선택 Agent | 연회색 | `#D1D5DB` |
| Agent 실행 중 | 파란색 점선 애니메이션 | `#3B82F6` |
| Tool 성공 | 녹색 체크 ✅ | `#10B981` |
| Tool 실패 | 적색 X ❌ | `#EF4444` |
| Primary Evidence | 금색 별 ★ | `#F59E0B` |
| Supporting Evidence | 은색 별 ☆ | `#9CA3AF` |
| Answer Slot | 보라색 박스 | `#7C3AED` |
| Memory 저장됨 | 파란색 아이콘 📝 | `#2563EB` |
| Long-term 저장 차단 | 적색 자물쇠 🔒 | `#EF4444` |

---

## 13. Trace / DB 테이블 설계

### ai_trace_event (최상위 요청 단위)

```sql
CREATE TABLE ai_trace_event (
    trace_id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id          VARCHAR(64) NOT NULL UNIQUE,
    session_id          VARCHAR(64),
    user_query          TEXT        NOT NULL,
    user_query_masked   TEXT,
    intent_name         VARCHAR(64),
    intent_confidence   NUMERIC(4,3),
    execution_strategy  VARCHAR(16),
    total_latency_ms    INTEGER,
    final_status        VARCHAR(16) NOT NULL,  -- SUCCESS / PARTIAL / FAILED / FALLBACK
    risk_flags          JSONB,
    schema_version      VARCHAR(8)  DEFAULT 'v2.0',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_trace_event_session ON ai_trace_event(session_id);
CREATE INDEX idx_trace_event_created ON ai_trace_event(created_at);
-- 보관 기간: 1년
```

### ai_decision_trace (Leader Decision 전체)

```sql
CREATE TABLE ai_decision_trace (
    decision_id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id            UUID        NOT NULL REFERENCES ai_trace_event(trace_id),
    decision_payload    JSONB       NOT NULL,  -- Leader Decision Schema 전체
    decision_reason     TEXT,
    decision_rules_applied JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_decision_trace_trace ON ai_decision_trace(trace_id);
-- 보관 기간: 1년
```

### ai_concept_detection (Concept 감지 결과)

```sql
CREATE TABLE ai_concept_detection (
    concept_det_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id        UUID        NOT NULL REFERENCES ai_trace_event(trace_id),
    concept_name    VARCHAR(64) NOT NULL,
    category        VARCHAR(16) NOT NULL CHECK (category IN ('core','supporting','reference')),
    confidence      NUMERIC(4,3) NOT NULL,
    threshold       NUMERIC(4,3) NOT NULL,
    promoted_from   VARCHAR(16),
    demoted_from    VARCHAR(16),
    reason          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_concept_det_trace ON ai_concept_detection(trace_id);
CREATE INDEX idx_concept_det_name  ON ai_concept_detection(concept_name);
-- 보관 기간: 1년
```

### ai_agent_selection (Agent 선택/미선택 기록)

```sql
CREATE TABLE ai_agent_selection (
    agent_sel_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id        UUID        NOT NULL REFERENCES ai_trace_event(trace_id),
    agent_name      VARCHAR(64) NOT NULL,
    selected        BOOLEAN     NOT NULL,
    role            VARCHAR(64),
    score           NUMERIC(4,3),
    reason          TEXT        NOT NULL,
    execution_mode  VARCHAR(16),               -- lightweight / normal
    tools_assigned  JSONB,                     -- ["RATE_LOOKUP", "RATE_RULE_LOOKUP"]
    depends_on      JSONB,                     -- ["PRODUCT_AGENT"]
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_agent_sel_trace ON ai_agent_selection(trace_id);
CREATE INDEX idx_agent_sel_agent ON ai_agent_selection(agent_name, selected);
-- 보관 기간: 1년
```

### ai_tool_execution (Tool 실행 결과)

```sql
CREATE TABLE ai_tool_execution (
    tool_exec_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id        UUID        NOT NULL REFERENCES ai_trace_event(trace_id),
    agent_name      VARCHAR(64) NOT NULL,
    tool_name       VARCHAR(64) NOT NULL,
    input_params    JSONB,
    output_data     JSONB,
    output_masked   JSONB,                     -- 민감정보 마스킹 버전
    latency_ms      INTEGER,
    status          VARCHAR(16) NOT NULL CHECK (status IN ('SUCCESS','FAILED','TIMEOUT','FALLBACK')),
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tool_exec_trace ON ai_tool_execution(trace_id);
CREATE INDEX idx_tool_exec_tool  ON ai_tool_execution(tool_name, status);
-- 보관 기간: 90일
```

### ai_evidence_trace (Evidence 수집 기록)

```sql
CREATE TABLE ai_evidence_trace (
    evidence_id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id                UUID        NOT NULL REFERENCES ai_trace_event(trace_id),
    tool_exec_id            UUID        REFERENCES ai_tool_execution(tool_exec_id),
    source_tool             VARCHAR(64) NOT NULL,
    source_agent            VARCHAR(64) NOT NULL,
    data_quality_score      NUMERIC(4,3),
    slot_relevance_score    NUMERIC(4,3),
    latency_bonus           NUMERIC(4,3),
    final_score             NUMERIC(4,3) NOT NULL,
    raw_content             JSONB,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_evidence_trace_trace ON ai_evidence_trace(trace_id);
CREATE INDEX idx_evidence_score       ON ai_evidence_trace(final_score DESC);
-- 보관 기간: 90일
```

### ai_answer_slot_ranking (Answer Slot별 Evidence 순위)

```sql
CREATE TABLE ai_answer_slot_ranking (
    slot_rank_id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id                UUID        NOT NULL REFERENCES ai_trace_event(trace_id),
    slot_id                 VARCHAR(32) NOT NULL,
    slot_name               VARCHAR(64) NOT NULL,
    question_part           TEXT,
    answer_required         BOOLEAN     NOT NULL DEFAULT true,
    candidate_evidences     JSONB       NOT NULL,
    selected_evidence_id    UUID        REFERENCES ai_evidence_trace(evidence_id),
    supporting_evidence_ids JSONB,
    selection_reason        TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_slot_rank_trace ON ai_answer_slot_ranking(trace_id);
-- 보관 기간: 90일
```

### ai_validation_trace (Validation 결과)

```sql
CREATE TABLE ai_validation_trace (
    validation_id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id        UUID        NOT NULL REFERENCES ai_trace_event(trace_id),
    check_name      VARCHAR(64) NOT NULL,
    passed          BOOLEAN     NOT NULL,
    severity        VARCHAR(16) CHECK (severity IN ('info','warn','error')),
    detail          TEXT,
    action_taken    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_validation_trace  ON ai_validation_trace(trace_id);
CREATE INDEX idx_validation_failed ON ai_validation_trace(trace_id, passed) WHERE passed = false;
-- 보관 기간: 1년 (감사 목적)
```

### ai_memory_save_decision (Memory 저장 판단)

```sql
CREATE TABLE ai_memory_save_decision (
    mem_decision_id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id                UUID        NOT NULL REFERENCES ai_trace_event(trace_id),
    short_memory_saved      BOOLEAN     NOT NULL,
    short_memory_reason     TEXT,
    long_term_saved         BOOLEAN     NOT NULL,
    long_term_reason        TEXT,
    long_term_content       TEXT,
    sensitive_detected      BOOLEAN     NOT NULL DEFAULT false,
    masking_applied         BOOLEAN     NOT NULL DEFAULT false,
    masking_fields          JSONB,
    user_consent_required   BOOLEAN     NOT NULL DEFAULT false,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_mem_decision_trace ON ai_memory_save_decision(trace_id);
-- 보관 기간: 1년
```

### ai_final_answer_trace (최종 답변 기록)

```sql
CREATE TABLE ai_final_answer_trace (
    answer_id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id                UUID        NOT NULL REFERENCES ai_trace_event(trace_id),
    final_answer            TEXT        NOT NULL,
    final_answer_masked     TEXT,
    disclaimer_included     BOOLEAN     NOT NULL DEFAULT false,
    slots_resolved          JSONB,
    unresolved_slots        JSONB,
    latency_ms              INTEGER,
    token_count             INTEGER,
    model_used              VARCHAR(64),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_final_answer_trace ON ai_final_answer_trace(trace_id);
-- 보관 기간: 90일
```

### 테이블 보관 기간 요약

| 테이블 | 보관 기간 | 이유 |
|---|---|---|
| ai_trace_event | 1년 | 감사 추적 기본 단위 |
| ai_decision_trace | 1년 | XAI / 감사 목적 |
| ai_concept_detection | 1년 | 모델 분석 목적 |
| ai_agent_selection | 1년 | Agent 선택 패턴 분석 |
| ai_tool_execution | 90일 | Tool I/O 데이터 용량 고려 |
| ai_evidence_trace | 90일 | Evidence 데이터 용량 고려 |
| ai_answer_slot_ranking | 90일 | 운영 디버깅 목적 |
| ai_validation_trace | 1년 | 감사/컴플라이언스 목적 |
| ai_memory_save_decision | 1년 | 개인정보 처리 감사 |
| ai_final_answer_trace | 90일 | 답변 원문 용량 고려 |

---

## 14. 개발 Task 목록

### Phase 1. Decision Trace Schema 정리

```
Task ID: P1-T01
Task 이름: Leader Decision Schema v2.0 Pydantic 모델 정의
목적: 개선된 Leader Decision 구조를 Pydantic 모델로 정의
수정 대상 파일: backend/app/schemas/ai_gateway.py
입력: Section 8의 Schema 설계
출력: LeaderDecisionV2, ConceptItem, SelectedAgent, RejectedAgent, DecisionRule 모델
구현 내용: Pydantic v2 BaseModel 정의, JSONB 필드는 dict 타입, Optional 처리
완료 기준: mypy 타입 체크 통과, 예시 JSON으로 model_validate() 정상 실행
테스트 기준: test_schema_leader_decision.py — 정상/누락 필드 케이스 검증
```

```
Task ID: P1-T02
Task 이름: Concept 분류 구조 스키마 정의
목적: Core/Supporting/Reference 분류 및 강등 로직 스키마화
수정 대상 파일: backend/app/schemas/ai_gateway.py
입력: Section 4의 Concept 분류 기준
출력: ConceptCategory Enum, ConceptDetectionResult 모델
구현 내용: category 필드 추가, promoted_from/demoted_from 필드 추가
완료 기준: 기존 LeaderDecision과 schema_version 필드로 구분
테스트 기준: 기존 test_agent.py 정상 통과 확인
```

### Phase 2. Concept 분류 구조 구현

```
Task ID: P2-T01
Task 이름: Concept confidence threshold 기반 분류 로직 구현
목적: 감지된 Concept를 Core/Supporting/Reference로 자동 분류
수정 대상 파일: backend/app/agents/leader.py
입력: _analyze_intent() 반환값에 concept별 confidence 포함
출력: _classify_concepts(concepts) → {"core": [], "supporting": [], "reference": []}
구현 내용: CONCEPT_THRESHOLDS dict 정의, confidence 기반 분류, 강등 로직
완료 기준: "대출 금리와 서류 알려줘" 입력 시 INTEREST_RATE, REQUIRED_DOCUMENT가 core에 위치
테스트 기준: test_agent.py에 분류 케이스 3개 이상 추가
```

```
Task ID: P2-T02
Task 이름: Decision Rule Evaluation 로직 구현
목적: Concept 분류 결과 → Agent 선택 규칙 적용
수정 대상 파일: backend/app/agents/leader.py
입력: classified_concepts dict
출력: {"triggered_rules": [...], "required_agents": [...], "optional_agents": [...]}
구현 내용: DECISION_RULES 리스트 정의, rule별 concept 조건 평가
완료 기준: INTEREST_RATE Core → R001 트리거 → RATE_AGENT 필수 선택
테스트 기준: 단위 테스트 — 각 Rule별 트리거 케이스
```

### Phase 3. Agent 선택/미선택 사유 구현

```
Task ID: P3-T01
Task 이름: Agent 선택/미선택 사유 Trace 저장 구현
목적: Leader가 각 Agent를 선택/미선택한 이유를 DB에 기록
수정 대상 파일: backend/app/agents/leader.py, backend/app/trace/trace_service.py
입력: Decision Rule 평가 결과
출력: ai_agent_selection 테이블에 선택/미선택 레코드 저장
구현 내용: _save_agent_selection_trace() 메서드 추가, selected=True/False 기록
완료 기준: 요청 1건 처리 후 ai_agent_selection에 4개 레코드 (Agent 4종 모두)
테스트 기준: test_trace.py — SEARCH_AGENT 미선택 레코드 확인
```

### Phase 4. Tool Execution Trace 구현

```
Task ID: P4-T01
Task 이름: ai_tool_execution 테이블 Alembic 마이그레이션
목적: Tool 실행 결과 저장 테이블 생성
수정 대상 파일: backend/alembic/versions/XXX_add_tool_execution.py
입력: Section 13의 ai_tool_execution 테이블 설계
출력: 마이그레이션 파일, alembic upgrade head 정상 완료
완료 기준: alembic upgrade head 후 테이블 존재 확인
테스트 기준: test_health.py에 테이블 존재 체크 추가
```

```
Task ID: P4-T02
Task 이름: Tool 실행 시 Trace 자동 저장
목적: 모든 Tool 호출 결과를 ai_tool_execution에 기록
수정 대상 파일: backend/app/tools/tool_gateway.py
입력: invoke_tool() 호출 결과
출력: ai_tool_execution 레코드 저장, latency_ms 측정 포함
구현 내용: time.perf_counter()로 latency 측정, 민감 필드 output_masked 생성
완료 기준: RATE_LOOKUP 1회 호출 후 ai_tool_execution에 레코드 생성
테스트 기준: test_tool.py — trace 저장 확인
```

### Phase 5. Answer Slot Ranking 구현

```
Task ID: P5-T01
Task 이름: Answer Slot 추출 로직 구현
목적: 복합 질문에서 질문 항목별 Slot 분리
수정 대상 파일: backend/app/agents/leader.py
입력: intent + Core Concept 목록
출력: List[AnswerSlot] — slot 이름, question_part, keywords
구현 내용: SLOT_CONCEPT_MAP dict (INTEREST_RATE→interest_rate 등), Slot 생성 로직
완료 기준: "금리와 서류 알려줘" → [interest_rate, required_document] 슬롯 생성
테스트 기준: 단일/복합 질문 4케이스
```

```
Task ID: P5-T02
Task 이름: Evidence → Slot 매핑 및 Ranking 구현
목적: 수집된 Evidence를 Slot별로 점수화하여 최적 Evidence 선택
수정 대상 파일: backend/app/trace/evidence_scorer.py
입력: List[Evidence], List[AnswerSlot]
출력: List[AnswerSlotRanking] — 슬롯별 선택 Evidence
구현 내용: 기존 Evidence 점수 체계 재활용, slot_relevance 점수 슬롯 키워드 매칭으로 산정
완료 기준: interest_rate slot → RATE_LOOKUP이 1순위 선택
테스트 기준: test_evidence_scorer.py — 슬롯별 랭킹 케이스
```

### Phase 6. Validation 단계 구현

```
Task ID: P6-T01
Task 이름: Validation 파이프라인 구현
목적: 답변 생성 전 10개 항목 검증
수정 대상 파일: backend/app/agents/validator.py (신규)
입력: Answer Slot Ranking 결과 + Evidence 데이터
출력: ValidationResult (passed/failed 항목, risk_flags, actions_taken)
구현 내용: ValidationChecker 클래스, check_freshness/check_pii/check_hallucination 등 메서드
완료 기준: PII 감지 케이스 — 주민번호 패턴 포함 시 failed 반환
테스트 기준: test_validation.py — 각 체크 항목별 케이스
```

### Phase 7. Memory Save Decision 구현

```
Task ID: P7-T01
Task 이름: Memory Save Decision 로직 구현
목적: 최종 답변 후 저장 여부 자동 판단
수정 대상 파일: backend/app/agents/leader.py, backend/app/agents/memory.py
입력: FinalAnswer + ValidationResult
출력: MemorySaveDecision (short_memory_save, long_term_save, masking_applied)
구현 내용: SENSITIVE_PATTERNS 리스트 정의, 저장 가치 판단 로직, Long-term 저장 금지 조건
완료 기준: RATE_SIMULATION 결과 (소득 포함) 시 Long-term 저장 차단 확인
테스트 기준: test_memory_decision.py
```

### Phase 8. Decision Graph UI 개선

```
Task ID: P8-T01
Task 이름: Chat UI에 Summary View 추가
목적: 운영자가 Decision 결과를 한눈에 확인
수정 대상 파일: backend/app/main.py (또는 templates/)
입력: ai_trace_event + ai_agent_selection
출력: 실행된 Agent, Tool, 처리시간, 위험 플래그 표시 UI
구현 내용: 기존 Chat UI에 사이드 패널 추가 (Jinja2 템플릿)
완료 기준: Chat 페이지에서 Summary 패널 표시
테스트 기준: 수동 확인 (브라우저)
```

```
Task ID: P8-T02
Task 이름: Decision Trace View / Evidence View 추가
목적: Concept 계층, Agent 선택 사유, Tool 결과를 상세 확인
수정 대상 파일: backend/app/main.py (또는 templates/)
입력: ai_decision_trace + ai_tool_execution + ai_answer_slot_ranking
출력: Concept 배지, Agent 선택/미선택 이유 패널, Tool 실행 결과 패널
완료 기준: Core/Supporting/Reference Concept 색상 구분 표시
테스트 기준: 수동 확인
```

### Phase 9. DB 저장 구조 적용

```
Task ID: P9-T01
Task 이름: 신규 Trace 테이블 Alembic 마이그레이션 일괄 적용
목적: Section 13의 10개 테이블 생성
수정 대상 파일: backend/alembic/versions/XXX_trace_v2.py
입력: Section 13의 테이블 DDL
출력: 마이그레이션 파일 1개, alembic upgrade head 정상
완료 기준: 10개 테이블 모두 생성 확인
테스트 기준: alembic downgrade -1 → upgrade head 정상 왕복
```

### Phase 10. 테스트 및 운영 검증

```
Task ID: P10-T01
Task 이름: 통합 테스트 전체 케이스 업데이트
목적: Phase 1~9 구현 이후 전체 pytest 통과
수정 대상 파일: backend/tests/test_chat.py, test_agent.py, test_trace.py 등
입력: 개선된 Decision Graph
출력: pytest 전체 통과 (기존 케이스 + 신규 케이스)
완료 기준: docker compose exec backend pytest 전체 GREEN
테스트 기준: 의도별 케이스 — 단일/복합/UNKNOWN_INTENT/민감정보 포함
```

---

## 15. MVP 우선순위

| 순위 | 항목 | Phase | 이유 |
|---|---|---|---|
| 1 | Concept Core/Supporting/Reference 분류 | 2 | Leader 판단 근거의 기반 |
| 2 | Agent 선택/미선택 사유 Trace 저장 | 3 | 운영자 가시성 핵심 |
| 3 | RATE_LOOKUP vs RATE_SIMULATION 분기 | 2 | 불필요한 시뮬레이션 호출 방지 |
| 4 | SEARCH_AGENT 기본 미선택 처리 | 3 | 역할 경계 명확화 |
| 5 | Answer Slot Ranking | 5 | 복합 질문 품질 핵심 |
| 6 | PII 검증 (민감정보 탐지 + 마스킹) | 6 | 금융 AI 필수 안전 요건 |
| 7 | Memory Save Decision 최소 구현 | 7 | Long-term 저장 위험 차단 |
| 8 | Tool latency 측정 + Trace 저장 | 4 | 성능 모니터링 기반 |
| 9 | Leader Decision Schema v2.0 | 1 | 전체 구조 기반 |
| 10 | Summary View UI | 8 | 운영자 확인 인터페이스 |

---

## 16. 나중에 확장할 항목

| 항목 | 제외 이유 | 확장 조건 |
|---|---|---|
| 실시간 그래프 애니메이션 | MVP에서 복잡도 대비 가치 낮음 | 운영 단계 UX 요구사항 확정 후 |
| 고급 Re-ranking ML 모델 | Evidence 점수 체계로 충분 | 대화 데이터 축적 후 |
| 복잡한 Long-term 개인화 메모리 | 민감정보 처리 법적 검토 필요 | 법률 검토 완료 후 |
| Concept 자동 온톨로지 확장 | MVP 개발 금지 범위 | Phase 11+ |
| 관리자 고급 필터 / 대시보드 | 운영 단계 요구사항 수집 필요 | 운영 6개월 후 |
| SEARCH_AGENT 상담이력 심화 | 상담이력 DB 연동 미완료 | 실 DB 연동 완료 후 |
| RATE_SIMULATION 고도화 (ML) | 실제 API 연계 미완료 | 실제 코어뱅킹 API 연계 후 |
| 사용자 동의 기반 Long-term Memory | 법적 요건 확인 필요 | 개인정보 처리 방침 수립 후 |

---

## 17. 리스크 및 주의사항

| 리스크 | 심각도 | 완화 방법 |
|---|---|---|
| **PII 미탐지** — 비정형 표현의 주민번호/계좌번호 탐지 실패 | 높음 | 정규식 패턴 외 LLM 기반 PII 탐지 보조 레이어 추가 검토 |
| **Concept confidence 오산정** — LLM 없이 규칙 기반 confidence 부정확 | 중간 | confidence 산정 로직 문서화, 테스트 케이스로 경계값 검증 |
| **PRODUCT_AGENT 선행 의존성** — PRODUCT_RESOLVE 실패 시 다른 Agent도 product_id 없이 실행 | 중간 | product_id=null fallback 처리, 각 Tool이 product_id 없이도 기본 동작 가능하도록 설계 |
| **Answer Slot 오탐** — 단일 질문을 복합 질문으로 오탐 | 낮음 | 슬롯 키워드 매칭 임계값 설정, 불확실하면 단일 슬롯으로 보수적 처리 |
| **Long-term Memory 저장 판단 오류** — 비민감으로 잘못 분류된 민감정보 저장 | 높음 | 저장 전 2단계 검증, 기본값은 "저장 안 함" |
| **Validation 성능 저하** — 10개 검증 항목이 응답 지연 유발 | 낮음 | 검증 항목 병렬 실행, 타임아웃 200ms 설정 후 실패 시 경고만 |
| **Schema 버전 관리** — v2.0 전환 후 기존 Trace와 호환 문제 | 낮음 | schema_version 필드로 구분, 기존 테이블 유지 + 신규 테이블 추가 방식 |
| **Mock API 금리 유효일 만료** — Mock 데이터 갱신 없음 | 낮음 (Mock) | 실제 API 연계 시 유효일 자동 체크 필수, Mock은 현재 날짜 기반 동적 생성으로 대체 |

---

> 이 문서는 Decision Graph v2.0 설계의 기준 문서입니다.  
> 구현 변경 시 이 문서와 [CLAUDE.md](../CLAUDE.md)의 Long Memory 섹션을 함께 갱신하세요.
