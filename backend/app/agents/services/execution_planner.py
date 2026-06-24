from __future__ import annotations

from app.knowledge.concept_service import get_apis_by_concept
from app.schemas.ai_gateway import ExecutionPlan, ExecutionStep


class ExecutionPlanner:
    def build_steps(self, db, route_result) -> tuple[list[ExecutionStep], set[str]]:
        steps: list[ExecutionStep] = []
        seen_apis: set[str] = set()

        for route_item in route_result.routing:
            for concept_id in route_item.concept_ids:
                for api in get_apis_by_concept(db, concept_id):
                    if api.api_id in seen_apis:
                        continue
                    seen_apis.add(api.api_id)
                    steps.append(
                        ExecutionStep(
                            step_index=len(steps),
                            agent_id=route_item.agent_id,
                            concept_id=concept_id,
                            api_id=api.api_id,
                            params={},
                        )
                    )

        return steps, seen_apis

    def build_plan(
        self,
        *,
        request_id: str,
        message: str,
        detected_concepts: list[str],
        routed_agents: list[str],
        steps: list[ExecutionStep],
    ) -> ExecutionPlan:
        return ExecutionPlan(
            request_id=request_id,
            message=message,
            detected_concepts=detected_concepts,
            routed_agents=routed_agents,
            steps=steps,
        )

