"""policy_formatter.py — 정책/서류/상담이력 API 응답 포맷터."""

from __future__ import annotations

from app.agents.formatters.base import AbstractFormatter
from app.schemas.ai_gateway import StepResult


class PolicyFormatter(AbstractFormatter):
    supported_apis = [
        "MOCK_POLICY_LOOKUP",
        "MOCK_DOCUMENT_SEARCH",
        "MOCK_COUNSELING_HISTORY",
    ]

    def format_single(self, result: StepResult, message: str = "") -> str:
        d = result.data if isinstance(result.data, dict) else {}
        api = result.api_id

        if api == "MOCK_DOCUMENT_SEARCH":
            docs = d.get("documents", [])
            if not docs:
                return "서류 정보를 조회할 수 없었습니다."
            lines = ["■ 필요서류"]
            for doc in docs:
                lines.append(f"  · {doc.get('name','')}")
            return "\n".join(lines)

        if api == "MOCK_POLICY_LOOKUP":
            policies: list[dict] = d.get("policies", [])
            if not policies:
                return "정책/약관 정보를 조회할 수 없었습니다."
            lines = ["■ 정책/약관 안내"]
            for pol in policies[:3]:
                title = pol.get("title", "")
                content = pol.get("content", "")
                if title:
                    lines.append(f"  · {title}")
                    if content:
                        lines.append(f"    {content[:120]}")
            return "\n".join(lines)

        if api == "MOCK_COUNSELING_HISTORY":
            histories: list[dict] = d.get("histories", [])
            if not histories:
                return "상담 이력을 조회할 수 없었습니다."
            lines = ["■ 상담 이력"]
            for h in histories[:5]:
                date = h.get("counseling_date", "")
                topic = h.get("topic", "")
                if topic:
                    lines.append(f"  · [{date}] {topic}")
            return "\n".join(lines)

        return ""

    def format_summary(self, result: StepResult) -> list[str]:
        data = result.data if isinstance(result.data, dict) else {}
        api = result.api_id

        if api == "MOCK_POLICY_LOOKUP":
            lines = ["■ 정책/약관"]
            for pol in data.get("policies", [])[:3]:
                title = pol.get("title", "")
                content = pol.get("content", "")
                if title:
                    lines.append(f"  · {title}")
                    if content:
                        lines.append(f"    {content[:100]}")
            return lines

        if api == "MOCK_DOCUMENT_SEARCH":
            lines = ["■ 필요서류"]
            for doc in data.get("documents", [])[:5]:
                name = doc.get("name", "")
                if name:
                    lines.append(f"  · {name}")
            return lines

        if api == "MOCK_COUNSELING_HISTORY":
            lines = ["■ 상담 이력"]
            for h in data.get("histories", [])[:3]:
                date = h.get("counseling_date", "")
                topic = h.get("topic", "")
                if topic:
                    lines.append(f"  · [{date}] {topic}")
            return lines

        return [f"■ {api}"]
