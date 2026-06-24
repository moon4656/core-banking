# executor.py — 실행 계획(ExecutionPlan)의 각 단계를 순서대로 실행한다
#
# [실행 흐름]
#   1. Planner가 만든 ExecutionPlan의 steps를 순서대로 처리
#   2. 각 step마다 Tool Hub(invoke_tool)를 통해 외부 API 호출
#   3. 호출 결과를 TraceEvent(TOOL_INVOKED)로 기록
#   4. 성공한 결과는 EvidenceReference(근거)로도 기록 — 신뢰도 점수 실제 계산
#   5. 성공/실패와 무관하게 StepResult를 생성해 반환 (오류가 전체 실행을 멈추지 않는다)
#
# [설계 원칙]
#   Agent가 API URL을 직접 알면 안 된다 — 반드시 invoke_tool을 경유한다.
#   한 step 실패가 다음 step 실행을 막으면 안 된다 — Tool Hub가 예외를 흡수한다.
#
# [intent 파라미터 추가 이유]
#   evidence_scorer가 intent_relevance_score를 계산하려면 의도 정보가 필요하다.
#   ExecutionPlan에 intent를 추가하거나, execute_plan에 별도 인자로 전달한다.
#   현재는 별도 인자 방식을 사용해 하위 호환성을 유지한다.

from sqlalchemy.orm import Session

from app.schemas.ai_gateway import ExecutionPlan, StepResult
from app.tools.tool_gateway import invoke_tool
from app.trace.evidence_service import save_evidence_with_score
from app.trace.trace_service import Timer, record_event


async def execute_plan(
    db: Session,
    plan: ExecutionPlan,
    intent: str = "INQUIRY",   # Leader Agent가 분석한 의도 — Evidence 점수 계산에 사용
) -> list[StepResult]:
    """
    ExecutionPlan의 모든 step을 순서대로 실행하고 결과 목록을 반환한다.

    step이 하나도 없으면 빈 리스트를 반환한다 (정상 동작).
    비동기(async) 함수인 이유: invoke_tool이 httpx 비동기 HTTP 요청을 사용하기 때문.

    [변경 사항 — v2]
    - response_latency_ms를 측정해 evidence에 기록한다
    - record_evidence() 대신 save_evidence_with_score()를 사용한다
      → confidence_score가 실제 계산값으로 저장된다 (이전: 항상 1.0)
    - intent 파라미터를 받아 intent_relevance_score도 계산한다
    """
    results: list[StepResult] = []

    for step in plan.steps:
        t = Timer()  # 이 step의 처리 시간 측정 시작

        # Tool Hub 경유 API 호출 — API URL, 인증 등은 Tool Hub 내부에서 처리
        tool_result = await invoke_tool(db, step.api_id, step.params)
        elapsed = t.elapsed_ms()

        # 호출 결과를 TraceEvent에 기록 (성공/실패 모두)
        record_event(
            db,
            request_id=plan.request_id,
            event_type="TOOL_INVOKED",
            agent_id=step.agent_id,
            tool_id=step.api_id,
            input_data={"api_id": step.api_id, "params": step.params},
            output_data={
                "status":       tool_result.status,
                "error":        tool_result.error,
                "latency_ms":   elapsed,     # 성능 모니터링용
            },
            status=tool_result.status,
            duration_ms=elapsed,
        )

        # 성공하고 데이터가 있을 때만 EvidenceReference(응답 근거) 기록
        # 빈 데이터나 오류 응답은 근거로 기록하지 않는다
        if tool_result.status == "success" and tool_result.data is not None:
            save_evidence_with_score(
                db=db,
                request_id=plan.request_id,
                concept_id=step.concept_id,
                source_id=step.api_id,
                content=tool_result.data,
                intent=intent,
                response_latency_ms=elapsed,
            )

        results.append(
            StepResult(
                step_index=step.step_index,
                api_id=step.api_id,
                status=tool_result.status,
                data=tool_result.data,
                error=tool_result.error,
            )
        )

    return results
