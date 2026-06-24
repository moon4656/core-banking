import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.agent_registry import route_by_concepts
from app.core.database import get_db
from app.knowledge.concept_service import detect_concepts_in_message
from app.models.eval_model import ConceptEvalCustomQuery, ConceptEvalItem, ConceptEvalRun
from app.models.knowledge_model import BusinessConceptRelation

router = APIRouter(prefix="/api/v1/admin/concept-eval", tags=["concept-eval"])

# ─────────────────────────────────────────────────────────────
# Option A: 라우팅 정확도 평가
#   expected_agents=[] → 라우팅 안 돼야 정답 (미구현 영역, 오탐 방지)
#   expected_agents=[...] → 해당 Agent로 라우팅되어야 정답
# ─────────────────────────────────────────────────────────────
_QUERY_SHEET: list[dict] = [
    # 대출 상품
    {"category": "대출 상품", "message": "신용대출 종류 알려줘",          "expected_agents": ["PRODUCT_AGENT"]},
    {"category": "대출 상품", "message": "마이너스통장 만들 수 있어?",     "expected_agents": ["PRODUCT_AGENT"]},
    # 금리
    {"category": "금리",     "message": "신용대출 금리 알려줘",            "expected_agents": ["PRODUCT_AGENT", "RATE_AGENT"]},
    {"category": "금리",     "message": "현재 대출금리가 얼마야?",          "expected_agents": ["RATE_AGENT"]},
    {"category": "금리",     "message": "1000만원 36개월 상환하면 얼마야?", "expected_agents": ["RATE_AGENT"]},
    {"category": "금리",     "message": "금리 우대 조건이 뭐야?",           "expected_agents": ["RATE_AGENT"]},
    # 필요서류 / 신청조건
    {"category": "필요서류", "message": "신용대출 필요서류 알려줘",         "expected_agents": ["PRODUCT_AGENT", "SEARCH_AGENT"]},
    {"category": "신청조건", "message": "신용대출 신청자격이 어떻게 되나요?","expected_agents": ["PRODUCT_AGENT"]},
    # 외화/환율 — MVP 미구현 영역, 라우팅 안 됨이 정답
    {"category": "외화/환율", "message": "오늘 달러 환율 알려줘",           "expected_agents": []},
    {"category": "외화/환율", "message": "USD 환율 조회",                  "expected_agents": []},
    {"category": "외화/환율", "message": "엔화 환율 얼마야?",               "expected_agents": []},
    {"category": "외화/환전", "message": "달러 환전하고 싶어요",            "expected_agents": []},
    {"category": "외화/환전", "message": "100만원어치 달러로 환전하면?",    "expected_agents": []},
    {"category": "해외송금",  "message": "미국으로 해외송금 하고 싶어",      "expected_agents": []},
    {"category": "외화예금",  "message": "외화예금 금리 알려줘",            "expected_agents": []},
    {"category": "외화예금",  "message": "달러예금 통장 만들고 싶어",       "expected_agents": []},
    # 알림 — MVP 미구현 영역
    {"category": "알림",     "message": "대출 만기 알림 받고 싶어요",       "expected_agents": []},
    {"category": "알림",     "message": "연체 알림 설정하고 싶어",          "expected_agents": []},
    # 복합 쿼리
    {"category": "복합 쿼리", "message": "신용대출 금리랑 필요서류 알려줘", "expected_agents": ["PRODUCT_AGENT", "RATE_AGENT", "SEARCH_AGENT"]},
    {"category": "복합 쿼리", "message": "대출 만기와 알림 설정 방법 알려줘","expected_agents": []},
    # 오탐 방지 — 금융 무관 질의, 라우팅 안 됨이 정답
    {"category": "오탐 방지", "message": "오늘 날씨 어때요?",              "expected_agents": []},
    {"category": "오탐 방지", "message": "안녕하세요",                     "expected_agents": []},
    {"category": "오탐 방지", "message": "현재 상태가 어때요?",             "expected_agents": []},
    {"category": "오탐 방지", "message": "해외여행 가고 싶어요",            "expected_agents": []},
    {"category": "오탐 방지", "message": "[시나리오 S018] 오늘 날씨가 어때요?", "expected_agents": []},
]


# ─────────────────────────────────────────────────────────────
# 스키마
# ─────────────────────────────────────────────────────────────

class EvalQuery(BaseModel):
    category: str
    message: str
    expected_agents: list[str] = []


class EvalResult(BaseModel):
    category: str
    message: str
    expected_agents: list[str]       # 기대 라우팅 Agent
    detected_concepts: list[str]     # 탐지된 Concept (참고용)
    direct_concepts: list[str] = []
    expanded_concepts: list[str] = []
    routed_agents: list[str]         # 실제 라우팅된 Agent
    true_positive: list[str]         # 올바르게 라우팅된 Agent
    false_positive: list[str]        # 불필요하게 라우팅된 Agent
    false_negative: list[str]        # 누락된 Agent
    precision: float | None
    recall: float | None
    f1_score: float | None
    grade: str


class BatchEvalResponse(BaseModel):
    total: int
    results: list[EvalResult]
    summary: dict


# ─── 저장 요청 ───────────────────────────────────────────────
class SaveEvalRunRequest(BaseModel):
    run_type: str           # "ALL" | "SELECTED"
    category: str | None
    results: list[EvalResult]
    summary: dict


# ─── 이력 응답 ───────────────────────────────────────────────
class EvalRunSummaryOut(BaseModel):
    run_id: str
    run_at: datetime
    run_type: str
    category: str | None
    total_queries: int
    avg_f1: float | None
    overall_grade: str


class EvalRunDetailOut(EvalRunSummaryOut):
    summary_json: dict | None
    items: list[EvalResult]


# ─────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────

def _grade(f1: float | None) -> str:
    if f1 is None:
        return "-"
    if f1 >= 0.9:
        return "A"
    if f1 >= 0.7:
        return "B"
    if f1 >= 0.5:
        return "C"
    if f1 >= 0.3:
        return "D"
    return "F"


def _score(expected: list[str], actual: list[str]) -> tuple[float | None, float | None, float | None]:
    """precision, recall, f1 반환.
    expected=[] → 라우팅 없음이 정답: actual=[]이면 1.0, 있으면 0.0.
    """
    exp_set = set(expected)
    act_set = set(actual)

    if not exp_set:
        score = 1.0 if not act_set else 0.0
        return score, score, score

    tp = exp_set & act_set
    precision = len(tp) / len(act_set) if act_set else 0.0
    recall = len(tp) / len(exp_set)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return round(precision, 4), round(recall, 4), round(f1, 4)


def _expand_via_relations(db: Session, concept_ids: list[str]) -> list[str]:
    """온톨로지 관계(weight≥0.7)로 탐지 concept를 확장. LeaderAgent와 동일 로직."""
    expanded = list(concept_ids)
    seen = set(concept_ids)
    for cid in concept_ids:
        relations = (
            db.query(BusinessConceptRelation)
            .filter(
                BusinessConceptRelation.source_concept_id == cid,
                BusinessConceptRelation.weight >= 0.7,
            )
            .all()
        )
        for rel in relations:
            if rel.target_concept_id not in seen:
                expanded.append(rel.target_concept_id)
                seen.add(rel.target_concept_id)
    return expanded


def _evaluate(query: EvalQuery, db: Session, expand: bool = True) -> EvalResult:
    # 1. Concept 탐지 (LeaderAgent와 동일)
    direct = [c.concept_id for c in detect_concepts_in_message(db, query.message)]
    all_detected = _expand_via_relations(db, direct) if expand else direct
    direct_set = set(direct)
    expanded = [c for c in all_detected if c not in direct_set]

    # 2. Agent 라우팅 (LeaderAgent와 동일)
    route_resp = route_by_concepts(db, all_detected)
    routed_agents = [r.agent_id for r in route_resp.routing]

    # 3. 기대 Agent vs 실제 라우팅 Agent 비교
    exp_set = set(query.expected_agents)
    routed_set = set(routed_agents)

    precision, recall, f1 = _score(list(exp_set), routed_agents)

    return EvalResult(
        category=query.category,
        message=query.message,
        expected_agents=query.expected_agents,
        detected_concepts=all_detected,
        direct_concepts=direct,
        expanded_concepts=expanded,
        routed_agents=routed_agents,
        true_positive=sorted(exp_set & routed_set),
        false_positive=sorted(routed_set - exp_set),
        false_negative=sorted(exp_set - routed_set),
        precision=precision,
        recall=recall,
        f1_score=f1,
        grade=_grade(f1),
    )


def _summarize(results: list[EvalResult]) -> dict:
    grades = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0, "-": 0}
    f1_values = []
    for r in results:
        grades[r.grade] = grades.get(r.grade, 0) + 1
        if r.f1_score is not None:
            f1_values.append(r.f1_score)

    avg_f1 = round(sum(f1_values) / len(f1_values), 4) if f1_values else None

    by_category: dict[str, dict] = {}
    for r in results:
        cat = r.category
        if cat not in by_category:
            by_category[cat] = {"total": 0, "f1_sum": 0.0, "grades": {}}
        by_category[cat]["total"] += 1
        if r.f1_score is not None:
            by_category[cat]["f1_sum"] += r.f1_score
        by_category[cat]["grades"][r.grade] = by_category[cat]["grades"].get(r.grade, 0) + 1

    category_summary = {
        cat: {
            "total": v["total"],
            "avg_f1": round(v["f1_sum"] / v["total"], 4) if v["total"] else None,
            "grades": v["grades"],
        }
        for cat, v in by_category.items()
    }

    return {
        "total": len(results),
        "avg_f1": avg_f1,
        "overall_grade": _grade(avg_f1),
        "grade_distribution": grades,
        "by_category": category_summary,
    }


# ─────────────────────────────────────────────────────────────
# 엔드포인트
# ─────────────────────────────────────────────────────────────

@router.get("/query-sheet", summary="카테고리별 사전 질의서 목록")
def get_query_sheet() -> list[dict]:
    return _QUERY_SHEET


@router.post("/batch", response_model=BatchEvalResponse, summary="질의서 일괄 라우팅 평가")
def batch_evaluate(
    queries: list[EvalQuery],
    expand: bool = True,
    db: Session = Depends(get_db),
) -> BatchEvalResponse:
    results = [_evaluate(q, db, expand=expand) for q in queries]
    return BatchEvalResponse(
        total=len(results),
        results=results,
        summary=_summarize(results),
    )


# ─────────────────────────────────────────────────────────────
# 커스텀 질의 영구 저장
# ─────────────────────────────────────────────────────────────

class CustomQueryOut(BaseModel):
    id: int
    category: str
    message: str
    expected_agents: list[str]


@router.get("/custom-queries", response_model=list[CustomQueryOut], summary="사용자 추가 질의 목록")
def list_custom_queries(db: Session = Depends(get_db)) -> list[CustomQueryOut]:
    rows = db.query(ConceptEvalCustomQuery).order_by(ConceptEvalCustomQuery.id).all()
    return [CustomQueryOut(id=r.id, category=r.category, message=r.message,
                           expected_agents=r.expected_agents or []) for r in rows]


@router.post("/custom-queries", response_model=CustomQueryOut, summary="커스텀 질의 추가")
def add_custom_query(body: EvalQuery, db: Session = Depends(get_db)) -> CustomQueryOut:
    row = ConceptEvalCustomQuery(
        category=body.category or "사용자 입력",
        message=body.message,
        expected_agents=body.expected_agents,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return CustomQueryOut(id=row.id, category=row.category, message=row.message,
                          expected_agents=row.expected_agents or [])


@router.put("/custom-queries/{query_id}", response_model=CustomQueryOut, summary="커스텀 질의 수정")
def update_custom_query(query_id: int, body: EvalQuery, db: Session = Depends(get_db)) -> CustomQueryOut:
    row = db.query(ConceptEvalCustomQuery).filter(ConceptEvalCustomQuery.id == query_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="custom query not found")
    row.category = body.category or "사용자 입력"
    row.message = body.message
    row.expected_agents = body.expected_agents
    db.commit()
    db.refresh(row)
    return CustomQueryOut(id=row.id, category=row.category, message=row.message,
                          expected_agents=row.expected_agents or [])


@router.delete("/custom-queries/{query_id}", summary="커스텀 질의 삭제")
def delete_custom_query(query_id: int, db: Session = Depends(get_db)):
    row = db.query(ConceptEvalCustomQuery).filter(ConceptEvalCustomQuery.id == query_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="custom query not found")
    db.delete(row)
    db.commit()
    return {"deleted": query_id}


# ─────────────────────────────────────────────────────────────
# 평가 결과 저장 / 이력 조회
# ─────────────────────────────────────────────────────────────

@router.post("/runs", response_model=EvalRunSummaryOut, summary="평가 결과 DB 저장")
def save_eval_run(body: SaveEvalRunRequest, db: Session = Depends(get_db)) -> EvalRunSummaryOut:
    run_id = str(uuid.uuid4())
    summary = body.summary

    run = ConceptEvalRun(
        run_id=run_id,
        run_type=body.run_type,
        category=body.category,
        total_queries=len(body.results),
        avg_f1=summary.get("avg_f1"),
        overall_grade=summary.get("overall_grade", "-"),
        summary_json=summary,
    )
    db.add(run)
    db.flush()

    for r in body.results:
        db.add(ConceptEvalItem(
            run_id=run_id,
            category=r.category,
            message=r.message,
            expected_agents=r.expected_agents,
            detected_concepts=r.detected_concepts,
            routed_agents=r.routed_agents,
            true_positive=r.true_positive,
            false_positive=r.false_positive,
            false_negative=r.false_negative,
            precision=r.precision,
            recall=r.recall,
            f1_score=r.f1_score,
            grade=r.grade,
        ))

    db.commit()
    db.refresh(run)

    return EvalRunSummaryOut(
        run_id=run.run_id,
        run_at=run.run_at,
        run_type=run.run_type,
        category=run.category,
        total_queries=run.total_queries,
        avg_f1=run.avg_f1,
        overall_grade=run.overall_grade,
    )


@router.get("/runs", response_model=list[EvalRunSummaryOut], summary="평가 이력 목록")
def list_eval_runs(limit: int = 30, db: Session = Depends(get_db)) -> list[EvalRunSummaryOut]:
    runs = (
        db.query(ConceptEvalRun)
        .order_by(ConceptEvalRun.run_at.desc())
        .limit(limit)
        .all()
    )
    return [
        EvalRunSummaryOut(
            run_id=r.run_id,
            run_at=r.run_at,
            run_type=r.run_type,
            category=r.category,
            total_queries=r.total_queries,
            avg_f1=r.avg_f1,
            overall_grade=r.overall_grade,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=EvalRunDetailOut, summary="평가 이력 상세")
def get_eval_run(run_id: str, db: Session = Depends(get_db)) -> EvalRunDetailOut:
    run = db.query(ConceptEvalRun).filter(ConceptEvalRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="eval run not found")

    items = db.query(ConceptEvalItem).filter(ConceptEvalItem.run_id == run_id).all()

    return EvalRunDetailOut(
        run_id=run.run_id,
        run_at=run.run_at,
        run_type=run.run_type,
        category=run.category,
        total_queries=run.total_queries,
        avg_f1=run.avg_f1,
        overall_grade=run.overall_grade,
        summary_json=run.summary_json,
        items=[
            EvalResult(
                category=it.category,
                message=it.message,
                expected_agents=it.expected_agents or [],
                detected_concepts=it.detected_concepts or [],
                routed_agents=it.routed_agents or [],
                true_positive=it.true_positive or [],
                false_positive=it.false_positive or [],
                false_negative=it.false_negative or [],
                precision=it.precision,
                recall=it.recall,
                f1_score=it.f1_score,
                grade=it.grade,
            )
            for it in items
        ],
    )


@router.delete("/runs/{run_id}", summary="평가 이력 삭제")
def delete_eval_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(ConceptEvalRun).filter(ConceptEvalRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="eval run not found")
    db.delete(run)
    db.commit()
    return {"deleted": run_id}
