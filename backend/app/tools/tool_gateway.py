# tool_gateway.py — Tool(API) 호출 허브
#
# [역할]
#   Agent가 외부 API를 직접 호출하면 안 된다.
#   반드시 이 파일의 invoke_tool()을 통해야 한다.
#
# [왜 허브를 경유하는가?]
#   1. API URL, 인증 정보가 코드에 분산되지 않는다 — api_catalog 테이블에서 중앙 관리
#   2. 오류를 흡수해 한 API 실패가 전체 요청을 중단시키지 않는다
#   3. Mock API → 실제 API 전환 시 이 파일과 api_catalog만 변경하면 된다
#
# [새 API를 추가하는 방법]
#   1. mock-api/main.py에 엔드포인트 추가
#   2. api_catalog 테이블에 레코드 삽입 (api_id, endpoint, method)
#   3. concept_api_mapping에 concept-api 연결 레코드 삽입
#   → 이 파일(tool_gateway.py)은 수정하지 않아도 된다

import time

import httpx
from sqlalchemy.orm import Session

from app.models.knowledge_model import ApiCatalog
from app.schemas.tool import ToolInvokeResponse

# PII/금융 민감 필드 — 이 키를 포함한 값은 Trace 저장 시 마스킹한다.
_SENSITIVE_KEYS: frozenset[str] = frozenset({
    "ssn", "rrn", "resident_registration_number",
    "account_no", "account_number",
    "credit_score", "credit_grade",
    "income", "annual_income",
    "employer", "company_name",
    "phone", "mobile", "email",
    "loan_limit", "available_limit",
    "address",
})


def _mask_output(data: dict | list | None) -> dict | None:
    """
    API 응답에서 민감 필드를 마스킹한 요약 딕셔너리를 반환한다.

    - dict: 민감 키 값을 "***"로 교체 (중첩 1 depth)
    - list: 첫 번째 항목만 처리해 {item_count, sample} 형태로 반환
    - None: None 반환
    """
    if data is None:
        return None
    if isinstance(data, list):
        sample = _mask_output(data[0]) if data else {}
        return {"item_count": len(data), "sample": sample}
    masked: dict = {}
    for k, v in data.items():
        if k.lower() in _SENSITIVE_KEYS:
            masked[k] = "***"
        elif isinstance(v, dict):
            masked[k] = {
                ik: ("***" if ik.lower() in _SENSITIVE_KEYS else iv)
                for ik, iv in v.items()
            }
        else:
            masked[k] = v
    return masked


def get_all_tools(db: Session) -> list[ApiCatalog]:
    """
    활성화된 전체 Tool(API) 목록을 반환한다.

    Tool은 별도 테이블 없이 api_catalog로 관리한다.
    api_catalog가 "호출 가능한 API 목록"이고, Tool은 그 별칭이다.
    """
    return db.query(ApiCatalog).filter(ApiCatalog.is_active == True).all()  # noqa: E712


async def invoke_tool(db: Session, api_id: str, params: dict) -> ToolInvokeResponse:
    """
    api_id로 api_catalog를 조회해 실제 HTTP 요청을 보낸다.

    [반환값 ToolInvokeResponse]
    - status="success" : API 호출 성공, data에 응답 JSON
    - status="error"   : API 호출 실패, error에 오류 메시지

    [중요] 예외를 raise하지 않고 status="error"로 반환한다.
    Executor는 한 step 실패 시 다음 step을 계속 실행할 수 있어야 한다.

    [파라미터 전달 방식]
    - GET  : params → query string (예: ?product_type=personal)
    - POST : params → JSON body
    현재 MVP에서는 params가 빈 dict({})이므로 전체 데이터를 가져온다.
    """
    # api_catalog에서 API 메타데이터 조회
    tool = (
        db.query(ApiCatalog)
        .filter(ApiCatalog.api_id == api_id, ApiCatalog.is_active == True)  # noqa: E712
        .first()
    )

    # 등록되지 않은 api_id — seed 데이터 누락이나 오타일 가능성이 높다
    if tool is None:
        return ToolInvokeResponse(
            api_id=api_id, status="error", data=None, error=f"tool not found: {api_id}"
        )

    _t0 = time.perf_counter()
    try:
        # timeout=10.0 : Mock API가 10초 이상 응답 없으면 TimeoutError
        # AsyncClient를 with 블록으로 사용해 요청 완료 후 커넥션을 자동으로 닫는다
        async with httpx.AsyncClient(timeout=10.0) as client:
            if tool.method.upper() == "GET":
                resp = await client.get(tool.endpoint, params=params)
            else:
                resp = await client.request(tool.method.upper(), tool.endpoint, json=params)

        resp.raise_for_status()
        latency_ms = int((time.perf_counter() - _t0) * 1000)
        data = resp.json()
        return ToolInvokeResponse(
            api_id=api_id,
            status="success",
            data=data,
            error=None,
            latency_ms=latency_ms,
            output_masked=_mask_output(data) if isinstance(data, (dict, list)) else None,
        )

    except Exception as exc:
        latency_ms = int((time.perf_counter() - _t0) * 1000)
        return ToolInvokeResponse(
            api_id=api_id,
            status="error",
            data=None,
            error=str(exc),
            latency_ms=latency_ms,
            output_masked=None,
        )
