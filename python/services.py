from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, FoodLossRecord, LossReason
from schemas import LossRecordInput
import hashlib
from datetime import datetime, timedelta, date, time
from typing import Dict, Any, List, Optional, Tuple

# main-test を優先した実装（競合で main-test のコードを採用）
from statistics import (
    calculate_weekly_statistics,
    get_total_grams_for_weeks,
    get_last_two_weeks,
)

# user 関連は既存の `user_service.py` を使う
from user_service import (
    get_user_by_username,
    get_user_by_id,
    register_new_user,
    update_user_points as update_user_points_internal,
    get_user_profile as get_user_profile_internal,
)


def get_all_loss_reasons(db: Session) -> List[str]:
    reasons = db.query(LossReason.reason_text).order_by(LossReason.id).all()
    return [r[0] for r in reasons]


def get_user_profile(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    return get_user_profile_internal(db, user_id)


def add_new_loss_record_direct(db: Session, record_data: Dict[str, Any]) -> int:
    reason = db.query(LossReason).filter_by(reason_text=record_data['reason_text']).first()
    if not reason:
        raise ValueError(f"無効な廃棄理由: {record_data['reason_text']}")

    new_record = FoodLossRecord(
        user_id=record_data['user_id'],
        item_name=record_data['item_name'],
        weight_grams=record_data['weight_grams'],
        loss_reason_id=reason.id,
    )

    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record.id


def calculate_weekly_points_logic(db: Session, user_id: int) -> Dict[str, Any]:
    # main-test 由来のロジックを採用
    last_week_grams, this_week_grams = get_last_two_weeks(db, user_id)
    past_4_weeks_total = get_total_grams_for_weeks(db, user_id, weeks_ago=4)
    baseline = (past_4_weeks_total / 4) if past_4_weeks_total > 0 else 0.0

    if last_week_grams > 0:
        rate_last_week = (last_week_grams - this_week_grams) / last_week_grams
    else:
        rate_last_week = 0.0 if this_week_grams == 0 else -1.0

    if baseline > 0:
        rate_baseline = (baseline - this_week_grams) / baseline
    else:
        rate_baseline = 0.0 if this_week_grams == 0 else -1.0

    final_reduction_rate = min(rate_last_week, rate_baseline)
    points_to_add = 0
    if final_reduction_rate > 0:
        reduction_percentage = int(final_reduction_rate * 100)
        calculated_points = reduction_percentage // 10
        points_to_add = min(calculated_points, 100)

    user = db.query(User).get(user_id)
    if user and points_to_add > 0:
        user.total_points += points_to_add
        db.commit()

    return {
        "points_added": points_to_add,
        "final_reduction_rate": round(final_reduction_rate * 100, 2),
        "rate_last_week": round(rate_last_week * 100, 2),
        "rate_baseline": round(rate_baseline * 100, 2),
    }


def get_weekly_stats(db: Session, user_id: int, target_date: date) -> Dict[str, Any]:
    # main-testの実装をそのまま使用
    return calculate_weekly_statistics(db, user_id)


def add_test_loss_records(db: Session, user_id: int) -> bool:
    if db.query(FoodLossRecord).filter_by(user_id=user_id).first():
        return False

    reason_expired = db.query(LossReason).filter_by(reason_text="期限切れ").first()
    reason_eaten = db.query(LossReason).filter_by(reason_text="料理後の廃棄").first()
    if not reason_expired or not reason_eaten:
        return False

    today = datetime.now()
    a_week_ago = today - timedelta(days=7)

    records = [
        FoodLossRecord(
            user_id=user_id,
            item_name="牛乳 (期限切れ)",
            weight_grams=1000.0,
            loss_reason_id=reason_expired.id,
            record_date=a_week_ago.isoformat()
        ),
        FoodLossRecord(
            user_id=user_id,
            item_name="カレーの食べ残し",
            weight_grams=350.5,
            loss_reason_id=reason_eaten.id,
            record_date=a_week_ago.isoformat()
        ),
        FoodLossRecord(
            user_id=user_id,
            item_name="ご飯 (期限切れ)",
            weight_grams=500.0,
            loss_reason_id=reason_expired.id,
            record_date=today.isoformat()
        )
    ]

    db.add_all(records)
    db.commit()
    return True
