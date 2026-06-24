"""notification_formatter.py — 알림 규칙/발송 API 응답 포맷터."""

from __future__ import annotations

from app.agents.formatters.base import AbstractFormatter
from app.schemas.ai_gateway import StepResult


class NotificationFormatter(AbstractFormatter):
    supported_apis = [
        "MOCK_NOTIFICATION_RULES",
        "MOCK_NOTIFICATION_SEND",
    ]

    def format_single(self, result: StepResult, message: str = "") -> str:
        d = result.data if isinstance(result.data, dict) else {}
        api = result.api_id

        if api == "MOCK_NOTIFICATION_RULES":
            rules_list: list[dict] = d.get("rules", [])
            if not rules_list:
                return "등록된 알림 규칙이 없습니다."
            lines = ["■ 알림 규칙 안내"]
            for r in rules_list:
                active_tag = "✓" if r.get("is_active") else "✗ (비활성)"
                lines.append(
                    f"  · [{r.get('trigger_type','')}] {r.get('name','')} "
                    f"— {r.get('channel','')} 채널 {active_tag}"
                )
                desc = r.get("description", "")
                if desc:
                    lines.append(f"    {desc}")
            return "\n".join(lines)

        if api == "MOCK_NOTIFICATION_SEND":
            status = d.get("status", "")
            msg = d.get("message", "")
            channel = d.get("channel", "")
            note = d.get("note", "")
            lines = ["■ 알림 발송 결과"]
            lines.append(f"  · 상태: {status}")
            lines.append(f"  · 채널: {channel}")
            lines.append(f"  · 내용: {msg}")
            if note:
                lines.append(f"  ※ {note}")
            return "\n".join(lines)

        return ""

    def format_summary(self, result: StepResult) -> list[str]:
        data = result.data if isinstance(result.data, dict) else {}
        api = result.api_id

        if api == "MOCK_NOTIFICATION_RULES":
            lines = ["■ 알림 규칙"]
            for rule in data.get("rules", [])[:4]:
                lines.append(
                    f"  · [{rule.get('trigger_type','')}] {rule.get('name','')} "
                    f"— {rule.get('channel','')} 채널"
                )
            return lines

        if api == "MOCK_NOTIFICATION_SEND":
            lines = ["■ 알림 발송"]
            lines.append(f"  · 상태: {data.get('status','')}")
            lines.append(f"  · 내용: {data.get('message','')}")
            return lines

        return [f"■ {api}"]
