from datetime import datetime

from sqlalchemy.orm import Session

from app.models.knowledge_model import NotificationRule

NOTIFICATION_RULES = [
    {
        "rule_id":           "RULE_RATE_CHANGE",
        "name":              "금리 변동 알림",
        "trigger_type":      "RATE_CHANGE",
        "channel":           "PUSH",
        "message_template":  "[금리 변동 알림] {product_name}의 금리가 {old_rate}% → {new_rate}%로 변경되었습니다.",
        "threshold":         0.1,
        "is_active":         True,
    },
    {
        "rule_id":           "RULE_MATURITY_30",
        "name":              "만기 30일 전 알림",
        "trigger_type":      "MATURITY",
        "channel":           "SMS",
        "message_template":  "[만기 안내] {product_name} 대출 만기일이 30일 후({date})입니다. 연장·상환 계획을 확인하세요.",
        "threshold":         30.0,
        "is_active":         True,
    },
    {
        "rule_id":           "RULE_MATURITY_7",
        "name":              "만기 7일 전 알림",
        "trigger_type":      "MATURITY",
        "channel":           "PUSH",
        "message_template":  "[긴급] {product_name} 대출 만기가 7일 후({date})입니다. 즉시 확인이 필요합니다.",
        "threshold":         7.0,
        "is_active":         True,
    },
    {
        "rule_id":           "RULE_OVERDUE_1",
        "name":              "연체 1일 경보",
        "trigger_type":      "OVERDUE",
        "channel":           "PUSH",
        "message_template":  "[연체 알림] {product_name} 납입일이 경과했습니다. 연체이자 발생을 방지하기 위해 즉시 납부하세요.",
        "threshold":         1.0,
        "is_active":         True,
    },
    {
        "rule_id":           "RULE_LIMIT_USAGE_90",
        "name":              "한도 90% 소진 알림",
        "trigger_type":      "LIMIT_USAGE",
        "channel":           "IN_APP",
        "message_template":  "[한도 경고] 마이너스통장 한도의 90% 이상({usage_rate}%)을 사용 중입니다. 잔여 한도를 확인하세요.",
        "threshold":         90.0,
        "is_active":         True,
    },
    {
        "rule_id":           "RULE_GRADE_UP",
        "name":              "신용등급 상승 알림",
        "trigger_type":      "GRADE_UP",
        "channel":           "PUSH",
        "message_template":  "[신용등급 상승] 신용등급이 {old_grade}등급에서 {new_grade}등급으로 개선되었습니다! 금리 인하 신청이 가능합니다.",
        "threshold":         None,
        "is_active":         True,
    },
]


def seed_notifications(db: Session) -> None:
    for data in NOTIFICATION_RULES:
        existing = db.query(NotificationRule).filter_by(rule_id=data["rule_id"]).first()
        if existing is None:
            db.add(
                NotificationRule(
                    rule_id=data["rule_id"],
                    name=data["name"],
                    trigger_type=data["trigger_type"],
                    channel=data["channel"],
                    message_template=data["message_template"],
                    threshold=data["threshold"],
                    is_active=data["is_active"],
                    created_at=datetime.utcnow(),
                )
            )

    db.commit()
    print(f"[notification_seed] {len(NOTIFICATION_RULES)} notification rules seeded.")
