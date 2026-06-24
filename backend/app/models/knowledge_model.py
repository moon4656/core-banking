from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB as JSON

from app.core.database import Base


class BusinessConcept(Base):
    __tablename__ = "business_concept"
    __table_args__ = {"comment": "업무 개념 단위. 금리·대출상품 등 도메인 지식의 핵심 노드. concept_id는 시스템 고유 식별자(예: CONCEPT_INTEREST_RATE), is_active=False이면 검색·라우팅에서 제외된다."}

    id         = Column(Integer, primary_key=True, index=True, comment="PK")
    concept_id = Column(String(100), unique=True, nullable=False, index=True, comment="시스템 내부 고유 식별자 (예: CONCEPT_INTEREST_RATE)")
    name       = Column(String(200), nullable=False, comment="사람이 읽는 개념 이름 (예: 금리)")
    description= Column(Text, nullable=True, comment="개념 설명")
    domain     = Column(String(100), nullable=True, comment="소속 도메인 (loan / rate / policy / document / counseling / customer)")
    is_active  = Column(Boolean, default=True, nullable=False, comment="False이면 검색·라우팅 제외")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class BusinessTermAlias(Base):
    __tablename__ = "business_term_alias"
    __table_args__ = {"comment": "업무 개념의 동의어·별칭. '이자율'로 검색해도 CONCEPT_INTEREST_RATE를 찾을 수 있도록 별도 테이블로 관리한다. 개념명 변경 없이 alias만 추가·삭제 가능."}

    id         = Column(Integer, primary_key=True, index=True, comment="PK")
    concept_id = Column(String(100), ForeignKey("business_concept.concept_id"), nullable=False, index=True, comment="FK → business_concept.concept_id")
    alias      = Column(String(200), nullable=False, comment="동의어·별칭 문자열 (예: 이자율, 대출금리)")
    language   = Column(String(20), default="ko", nullable=False, comment="언어 코드 (현재 ko만 사용)")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class BusinessConceptRelation(Base):
    __tablename__ = "business_concept_relation"
    __table_args__ = {"comment": "업무 개념 간 관계(온톨로지 엣지). weight≥0.7인 관계는 Leader Agent가 탐지된 concept을 자동 확장할 때 사용한다. MVP에서는 수동 등록만 허용하며 자동 추론은 구현하지 않는다."}

    id                = Column(Integer, primary_key=True, index=True, comment="PK")
    source_concept_id = Column(String(100), ForeignKey("business_concept.concept_id"), nullable=False, index=True, comment="관계 출발 concept (FK → business_concept.concept_id)")
    target_concept_id = Column(String(100), ForeignKey("business_concept.concept_id"), nullable=False, index=True, comment="관계 도착 concept (FK → business_concept.concept_id)")
    relation_type     = Column(String(100), nullable=False, comment="관계 유형: includes / requires / governed_by / has_condition / has_record")
    weight            = Column(Float, default=1.0, nullable=False, comment="관계 강도 (0.0~1.0). 0.7 미만이면 자동 확장에서 제외")
    created_at        = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class DataSourceCatalog(Base):
    __tablename__ = "data_source_catalog"
    __table_args__ = {"comment": "데이터 소스 카탈로그. DB 테이블·파일·외부 시스템 등 데이터 출처를 등록한다. ConceptDataMapping을 통해 특정 concept과 연결."}

    id              = Column(Integer, primary_key=True, index=True, comment="PK")
    source_id       = Column(String(100), unique=True, nullable=False, index=True, comment="시스템 고유 식별자 (예: DS_LOAN_TABLE)")
    name            = Column(String(200), nullable=False, comment="데이터 소스 이름")
    source_type     = Column(String(50), nullable=False, comment="소스 종류: postgresql / file / api")
    connection_info = Column(JSON, nullable=True, comment="접속 정보 JSON (예: {\"table\": \"loan_products\"})")
    is_active       = Column(Boolean, default=True, nullable=False, comment="False이면 조회 대상에서 제외")
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class ApiCatalog(Base):
    __tablename__ = "api_catalog"
    __table_args__ = {"comment": "Tool Hub가 호출할 수 있는 API(Tool) 목록. endpoint·method로 실제 HTTP 요청을 수행하며, is_active=False이면 호출하지 않는다. 새 Mock API 추가 시 이 테이블과 ConceptApiMapping에 레코드를 삽입한다."}

    id              = Column(Integer, primary_key=True, index=True, comment="PK")
    api_id          = Column(String(100), unique=True, nullable=False, index=True, comment="시스템 고유 식별자 (예: MOCK_RATE_LOOKUP)")
    name            = Column(String(200), nullable=False, comment="API 이름")
    endpoint        = Column(String(500), nullable=False, comment="HTTP 요청 URL (예: http://mock-api:8010/rates)")
    method          = Column(String(10), default="GET", nullable=False, comment="HTTP 메서드 (GET / POST)")
    description     = Column(Text, nullable=True, comment="API 기능 설명")
    request_schema  = Column(JSON, nullable=True, comment="요청 파라미터 JSON Schema (참고용)")
    response_schema = Column(JSON, nullable=True, comment="응답 구조 JSON Schema (참고용)")
    is_active       = Column(Boolean, default=True, nullable=False, comment="False이면 Tool Hub가 이 API를 호출하지 않음")
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class ConceptDataMapping(Base):
    __tablename__ = "concept_data_mapping"
    __table_args__ = {"comment": "업무 개념(concept)과 데이터 소스를 연결하는 매핑 테이블. field_path로 소스 내 특정 필드를 지정하고, priority로 다중 소스 간 우선순위를 제어한다."}

    id         = Column(Integer, primary_key=True, index=True, comment="PK")
    concept_id = Column(String(100), ForeignKey("business_concept.concept_id"), nullable=False, index=True, comment="FK → business_concept.concept_id")
    source_id  = Column(String(100), ForeignKey("data_source_catalog.source_id"), nullable=False, comment="FK → data_source_catalog.source_id")
    field_path = Column(String(500), nullable=True, comment="소스 내 필드 경로 (예: loan_products.interest_rate)")
    priority   = Column(Integer, default=0, nullable=False, comment="우선순위 — 낮을수록 먼저 사용")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class ConceptApiMapping(Base):
    __tablename__ = "concept_api_mapping"
    __table_args__ = {"comment": "업무 개념(concept)과 호출 가능한 API를 연결하는 매핑 테이블. Leader Agent가 탐지된 concept_id로 어떤 API를 호출할지 결정할 때 참조하며, priority로 호출 순서를 제어한다."}

    id         = Column(Integer, primary_key=True, index=True, comment="PK")
    concept_id = Column(String(100), ForeignKey("business_concept.concept_id"), nullable=False, index=True, comment="FK → business_concept.concept_id")
    api_id     = Column(String(100), ForeignKey("api_catalog.api_id"), nullable=False, comment="FK → api_catalog.api_id")
    priority   = Column(Integer, default=0, nullable=False, comment="우선순위 — 낮을수록 먼저 호출")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class CustomerProfile(Base):
    __tablename__ = "customer_profile"
    __table_args__ = {"comment": "대출 상담 고객 프로파일. 신용등급·연소득·직업유형을 저장하며 개인화 금리 조회에 활용된다."}

    id              = Column(Integer, primary_key=True, index=True, comment="PK")
    customer_id     = Column(String(100), unique=True, nullable=False, index=True, comment="고객 고유 ID (예: CUSTOMER_001)")
    name            = Column(String(100), nullable=False, comment="고객 이름")
    credit_grade    = Column(Integer, nullable=False, comment="신용등급 1(최우량)~10(위험)")
    annual_income   = Column(Integer, nullable=True, comment="연소득 (만원 단위)")
    employment_type = Column(String(50), nullable=True, comment="직업유형: 직장인 / 자영업자 / 프리랜서")
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class CreditGradeRate(Base):
    __tablename__ = "credit_grade_rate"
    __table_args__ = (
        UniqueConstraint("product_type", "credit_grade", name="uq_credit_grade_rate"),
        {"comment": "신용등급별 상품 적용 금리표. product_type × credit_grade 조합으로 min_rate/max_rate를 정의한다."},
    )

    id           = Column(Integer, primary_key=True, index=True, comment="PK")
    product_type = Column(String(100), nullable=False, index=True, comment="대출 상품 유형 (예: 직장인 신용대출)")
    credit_grade = Column(Integer, nullable=False, comment="신용등급 1~10")
    min_rate     = Column(Float, nullable=False, comment="최저 적용 금리 (%)")
    max_rate     = Column(Float, nullable=False, comment="최고 적용 금리 (%)")
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class IntentTermSynonym(Base):
    __tablename__ = "intent_term_synonym"
    __table_args__ = {"comment": "의도(intent) 감지용 동의어 사전. rate_agent 등이 사용자 메시지에서 의도를 판별할 때 참조한다. 코드 수정 없이 DB에서 용어를 추가·삭제할 수 있다."}

    id         = Column(Integer, primary_key=True, index=True, comment="PK")
    intent     = Column(String(100), nullable=False, index=True, comment="의도 레이블 (예: RATE_MIN, RATE_MAX)")
    term       = Column(String(200), nullable=False, comment="동의어 문자열 (예: 최저, 가장 낮은)")
    language   = Column(String(20), default="ko", nullable=False, comment="언어 코드")
    is_active  = Column(Boolean, default=True, nullable=False, comment="False이면 패턴 빌드에서 제외")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class NotificationRule(Base):
    __tablename__ = "notification_rule"
    __table_args__ = {"comment": "알림 발송 규칙 정의. trigger_type 조건이 충족되면 NOTIFICATION_AGENT가 알림을 생성한다."}

    id             = Column(Integer, primary_key=True, index=True, comment="PK")
    rule_id        = Column(String(100), unique=True, nullable=False, index=True, comment="규칙 고유 ID (예: RULE_RATE_CHANGE)")
    name           = Column(String(200), nullable=False, comment="규칙 이름")
    trigger_type   = Column(String(100), nullable=False, comment="트리거 유형: RATE_CHANGE / MATURITY / OVERDUE / LIMIT_USAGE / GRADE_UP")
    channel        = Column(String(50), nullable=False, comment="알림 채널: PUSH / SMS / EMAIL / IN_APP")
    message_template = Column(Text, nullable=False, comment="알림 메시지 템플릿 (변수: {product_name}, {rate}, {date} 등)")
    threshold      = Column(Float, nullable=True, comment="트리거 임계값 (예: 한도사용률 90%)")
    is_active      = Column(Boolean, default=True, nullable=False, comment="False이면 이 규칙은 실행하지 않음")
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False, comment="레코드 생성 일시 (UTC)")


class NotificationLog(Base):
    __tablename__ = "notification_log"
    __table_args__ = {"comment": "알림 발송 이력. NOTIFICATION_AGENT가 알림을 생성·발송할 때마다 1행 기록한다."}

    id           = Column(Integer, primary_key=True, index=True, comment="PK")
    rule_id      = Column(String(100), ForeignKey("notification_rule.rule_id"), nullable=True, index=True, comment="FK → notification_rule.rule_id")
    customer_id  = Column(String(100), nullable=True, index=True, comment="알림 대상 고객 ID")
    channel      = Column(String(50), nullable=False, comment="실제 발송 채널")
    message      = Column(Text, nullable=False, comment="실제 발송된 메시지 내용")
    status       = Column(String(20), nullable=False, default="SENT", comment="발송 상태: SENT / FAILED / PENDING")
    trigger_data = Column(JSON, nullable=True, comment="트리거 발생 시 캡처된 데이터 (금리값, 만기일 등) JSON")
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False, comment="발송 일시 (UTC)")
