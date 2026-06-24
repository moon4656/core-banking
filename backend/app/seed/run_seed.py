import structlog

from app.core.database import SessionLocal
from app.seed.concepts_seed import seed_concepts
from app.seed.agents_seed import seed_agents
from app.seed.tools_seed import seed_tools
from app.seed.mappings_seed import seed_mappings
from app.seed.relations_seed import seed_relations
from app.seed.customer_seed import seed_customers
from app.seed.notification_seed import seed_notifications
from app.seed.intent_synonyms_seed import run as seed_intent_synonyms

logger = structlog.get_logger()


def main() -> None:
    logger.info("seed.start")
    db = SessionLocal()
    try:
        seed_concepts(db)   # 업무 개념 + alias
        seed_agents(db)     # Agent 카탈로그
        seed_tools(db)      # API(Tool) 카탈로그
        seed_mappings(db)   # Agent-Concept, Concept-API 매핑
        seed_relations(db)  # 온톨로지 관계 (신용대출 → 금리 등)
        seed_customers(db)      # 고객 프로파일 + 신용등급별 금리표
        seed_notifications(db)      # 알림 규칙 기본 데이터
        seed_intent_synonyms(db)    # 의도 감지 동의어 사전
        logger.info("seed.complete")
    except Exception as e:
        db.rollback()
        logger.error("seed.failed", error=str(e))
        raise
    finally:
        db.close()


main()
