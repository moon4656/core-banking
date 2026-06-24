"""base.py — AbstractFormatter 정의 및 포맷터 등록 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.ai_gateway import StepResult


class AbstractFormatter(ABC):
    """API 도메인별 응답 포맷터 기반 클래스."""

    #: 이 포맷터가 처리하는 API ID 목록 (하위 클래스에서 선언)
    supported_apis: list[str] = []

    @abstractmethod
    def format_single(self, result: StepResult, message: str = "") -> str:
        """단일 결과 상세 포맷 — _single_result_answer 역할."""

    @abstractmethod
    def format_summary(self, result: StepResult) -> list[str]:
        """다중 결과 요약 라인 목록 — _template_answer 내부 라인 역할.

        반환값: ["■ 제목", "  · 라인1", "  · 라인2", ...]
        """
