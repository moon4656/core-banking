"""
run_eval.py — 골든 데이터셋 기반 AI 상담 정확도 평가 실행기

[실행 방법]
  docker compose exec backend python -m app.eval.run_eval
  docker compose exec backend python -m app.eval.run_eval --category intent
  docker compose exec backend python -m app.eval.run_eval --id S001,S002,S006
  docker compose exec backend python -m app.eval.run_eval --fail-fast

[채점 항목]
  ① 의도 분류 정확도  (intent)
  ② Concept 탐지율    (concept coverage)
  ③ Agent 선택 정확도 (agent routing)
  ④ 답변 키워드 포함률 (answer quality)
  ⑤ 답변 금지어 미포함 (answer safety)
  ⑥ Evidence 최소 건수 (evidence count)
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.eval.scenarios import SCENARIOS, Scenario

API_BASE = "http://localhost:8000"
CHAT_URL = f"{API_BASE}/api/v1/ai/chat"
TIMEOUT = 30.0


# ─────────────────────────────────────────────────────────────
# 채점 결과
# ─────────────────────────────────────────────────────────────

@dataclass
class DimScore:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ScenarioResult:
    scenario: Scenario
    status_code: int = 0
    response: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    latency_ms: int = 0
    scores: list[DimScore] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.error is None and all(s.passed for s in self.scores)

    @property
    def score_ratio(self) -> tuple[int, int]:
        return sum(1 for s in self.scores if s.passed), len(self.scores)


# ─────────────────────────────────────────────────────────────
# 채점 로직
# ─────────────────────────────────────────────────────────────

def _score(result: ScenarioResult) -> None:
    scenario = result.scenario
    exp = scenario.expected
    body = result.response

    plan = body.get("plan", {})
    detected = set(plan.get("detected_concepts", []))
    routed = set(body.get("plan", {}).get("routed_agents", []))
    intent = body.get("intent", {}).get("intent", "")
    answer = body.get("answer", "")
    evidence_count = body.get("evidence_count", 0)

    # ① 의도 분류
    if exp.intent:
        ok = intent == exp.intent
        result.scores.append(DimScore(
            "intent",
            ok,
            f"기대={exp.intent} 실제={intent}",
        ))

    # ② Concept 탐지율
    for cid in exp.must_detect_concepts:
        ok = cid in detected
        result.scores.append(DimScore(
            f"concept:{cid}",
            ok,
            f"{'탐지됨' if ok else '미탐지'} (detected={sorted(detected)})",
        ))

    # ③ Agent 선택 정확도
    for aid in exp.must_select_agents:
        # routed_agents 또는 decision_v2.selected_agents 둘 다 확인
        dv2_agents = {
            a.get("agent_id", "") if isinstance(a, dict) else a
            for a in (body.get("decision_v2", {}) or {}).get("selected_agents", [])
        }
        ok = (aid in routed) or (aid in dv2_agents)
        result.scores.append(DimScore(
            f"agent:{aid}",
            ok,
            f"{'선택됨' if ok else '미선택'} (routed={sorted(routed)})",
        ))

    # ④ 답변 키워드 포함
    for kw in exp.answer_must_contain:
        ok = kw in answer
        result.scores.append(DimScore(
            f"answer_contains:{kw}",
            ok,
            f"{'포함' if ok else '미포함'} (answer length={len(answer)})",
        ))

    # ⑤ 금지어 미포함
    for kw in exp.answer_must_not_contain:
        ok = kw not in answer
        result.scores.append(DimScore(
            f"answer_not_contains:{kw}",
            ok,
            f"{'안전' if ok else '⚠ 포함됨'}",
        ))

    # ⑥ Evidence 최소 건수
    if exp.min_evidence > 0:
        ok = evidence_count >= exp.min_evidence
        result.scores.append(DimScore(
            "evidence_count",
            ok,
            f"기대≥{exp.min_evidence} 실제={evidence_count}",
        ))


# ─────────────────────────────────────────────────────────────
# 실행기
# ─────────────────────────────────────────────────────────────

def run_scenario(scenario: Scenario, client: httpx.Client) -> ScenarioResult:
    result = ScenarioResult(scenario=scenario)
    try:
        t0 = time.monotonic()
        resp = client.post(
            CHAT_URL,
            json={"message": scenario.question, "session_id": f"eval-{scenario.id}"},
            timeout=TIMEOUT,
        )
        result.latency_ms = int((time.monotonic() - t0) * 1000)
        result.status_code = resp.status_code

        if resp.status_code != 200:
            result.error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            return result

        result.response = resp.json()
        _score(result)
    except Exception as exc:
        result.error = f"요청 실패: {exc}"
    return result


# ─────────────────────────────────────────────────────────────
# 리포트 출력
# ─────────────────────────────────────────────────────────────

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

def _status_icon(passed: bool) -> str:
    return PASS if passed else FAIL


def print_report(results: list[ScenarioResult], verbose: bool = False) -> None:
    print()
    print("=" * 72)
    print("📊 AI 상담 정확도 평가 리포트")
    print("=" * 72)

    category_stats: dict[str, list[bool]] = {}
    dim_stats: dict[str, list[bool]] = {}
    total_passed = 0

    for r in results:
        icon = _status_icon(r.passed)
        passed_n, total_n = r.score_ratio
        line = (
            f"{icon} [{r.scenario.id}] {r.scenario.question[:36]:<36} "
            f"({passed_n}/{total_n})  {r.latency_ms}ms"
        )
        print(line)

        if r.error:
            print(f"     💥 {r.error}")
        elif verbose or not r.passed:
            for s in r.scores:
                dim_icon = PASS if s.passed else FAIL
                print(f"     {dim_icon} {s.name:<35} {s.detail}")

        # 카테고리별 집계
        cat = r.scenario.category
        category_stats.setdefault(cat, []).append(r.passed)

        # 차원별 집계
        for s in r.scores:
            dim_key = s.name.split(":")[0]
            dim_stats.setdefault(dim_key, []).append(s.passed)

        if r.passed:
            total_passed += 1

    # ── 차원별 정확도 ─────────────────────────────────────────
    print()
    print("─" * 72)
    print("📐 차원별 정확도")
    print("─" * 72)
    dim_order = ["intent", "concept", "agent", "answer_contains",
                 "answer_not_contains", "evidence_count"]
    for dim in dim_order:
        vals = dim_stats.get(dim, [])
        if not vals:
            continue
        pct = sum(vals) / len(vals) * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        icon = PASS if pct >= 80 else (WARN if pct >= 60 else FAIL)
        print(f"  {icon} {dim:<22} [{bar}] {pct:5.1f}%  ({sum(vals)}/{len(vals)})")

    # ── 카테고리별 집계 ───────────────────────────────────────
    print()
    print("─" * 72)
    print("📁 카테고리별 통과율")
    print("─" * 72)
    for cat, vals in sorted(category_stats.items()):
        pct = sum(vals) / len(vals) * 100
        icon = PASS if pct >= 80 else (WARN if pct >= 60 else FAIL)
        print(f"  {icon} {cat:<12} {sum(vals)}/{len(vals)} ({pct:.0f}%)")

    # ── 전체 요약 ─────────────────────────────────────────────
    total = len(results)
    overall_pct = total_passed / total * 100 if total else 0
    print()
    print("=" * 72)
    icon = PASS if overall_pct >= 80 else (WARN if overall_pct >= 60 else FAIL)
    print(f"{icon} 전체 통과: {total_passed}/{total} ({overall_pct:.1f}%)")
    latencies = [r.latency_ms for r in results if r.latency_ms > 0]
    if latencies:
        print(f"⏱  응답시간: 평균 {sum(latencies)//len(latencies)}ms  "
              f"최대 {max(latencies)}ms  최소 {min(latencies)}ms")
    print("=" * 72)
    print()


def save_json_report(results: list[ScenarioResult], path: str) -> None:
    out = []
    for r in results:
        out.append({
            "id": r.scenario.id,
            "category": r.scenario.category,
            "question": r.scenario.question,
            "description": r.scenario.description,
            "passed": r.passed,
            "latency_ms": r.latency_ms,
            "error": r.error,
            "score_ratio": list(r.score_ratio),
            "scores": [{"name": s.name, "passed": s.passed, "detail": s.detail}
                       for s in r.scores],
            "intent": r.response.get("intent", {}).get("intent"),
            "detected_concepts": r.response.get("plan", {}).get("detected_concepts", []),
            "answer_preview": r.response.get("answer", "")[:100],
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"💾 JSON 리포트 저장됨: {path}")


# ─────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="AI 상담 골든 데이터셋 평가")
    parser.add_argument("--category", help="특정 카테고리만 실행 (intent/concept/agent/answer/edge)")
    parser.add_argument("--id", help="특정 시나리오 ID만 실행 (콤마 구분, 예: S001,S006)")
    parser.add_argument("--fail-fast", action="store_true", help="첫 실패 시 즉시 종료")
    parser.add_argument("--verbose", action="store_true", help="모든 채점 상세 출력")
    parser.add_argument("--json", help="JSON 리포트 저장 경로 (예: /tmp/eval_report.json)")
    args = parser.parse_args()

    # 시나리오 필터링
    scenarios = SCENARIOS
    if args.id:
        id_set = {s.strip() for s in args.id.split(",")}
        scenarios = [s for s in scenarios if s.id in id_set]
    if args.category:
        scenarios = [s for s in scenarios if s.category == args.category]

    if not scenarios:
        print("❌ 실행할 시나리오가 없습니다. --category 또는 --id 확인.")
        sys.exit(1)

    print(f"\n🚀 평가 시작: 총 {len(scenarios)}개 시나리오")
    print(f"   API: {CHAT_URL}")
    print()

    results: list[ScenarioResult] = []
    with httpx.Client() as client:
        for i, scenario in enumerate(scenarios, 1):
            print(f"  [{i:02d}/{len(scenarios)}] {scenario.id} — {scenario.question[:50]}", end=" ", flush=True)
            result = run_scenario(scenario, client)
            results.append(result)
            icon = PASS if result.passed else FAIL
            print(f"{icon}  ({result.latency_ms}ms)")

            if args.fail_fast and not result.passed:
                print(f"\n💥 fail-fast: {scenario.id} 실패로 중단")
                break

    print_report(results, verbose=args.verbose)

    if args.json:
        save_json_report(results, args.json)

    # 전체 통과 여부로 종료 코드 결정 (CI 연동용)
    total_passed = sum(1 for r in results if r.passed)
    sys.exit(0 if total_passed == len(results) else 1)


if __name__ == "__main__":
    main()
