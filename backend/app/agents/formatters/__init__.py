"""formatters — API 응답을 한국어 텍스트로 변환하는 포맷터 패키지.

leader.py의 _single_result_answer / _template_answer 로직을 도메인별로 분리한다.

사용법:
    from app.agents.formatters import format_single, format_multi

    # 단일 결과 (LLM 우회 상세 포맷)
    text = format_single(result, message)

    # 다중 결과 (fallback 요약 포맷)
    text = format_multi(results)
"""

from __future__ import annotations

from app.agents.formatters.registry import format_single, format_multi

__all__ = ["format_single", "format_multi"]
