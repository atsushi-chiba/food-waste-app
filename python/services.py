from sqlalchemy import func
from sqlalchemy.orm import Session
from models import User, FoodLossRecord, LossReason,arrange_suggest
# schemas削除：Renderビルド問題対応
from datetime import datetime, timedelta, date, time
from typing import Dict, Any, List, Optional, Tuple
import hashlib

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
from chatgpt_module import generate_recipe_from_text


def get_all_loss_reasons(db: Session) -> List[str]:
    reasons = db.query(LossReason.reason_text).order_by(LossReason.id).all()
    return [r[0] for r in reasons]


def get_user_profile(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    return get_user_profile_internal(db, user_id)


def add_new_loss_record_direct(db: Session, record_data: Dict[str, Any]) -> int:
    reason = (
        db.query(LossReason).filter_by(reason_text=record_data["reason_text"]).first()
    )
    if not reason:
        raise ValueError(f"無効な廃棄理由: {record_data['reason_text']}")

    new_record = FoodLossRecord(
        user_id=record_data["user_id"],
        item_name=record_data["item_name"],
        weight_grams=record_data["weight_grams"],
        loss_reason_id=reason.id,
    )

    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record.id


# ポイント付与の設定（寛容モード）
ONBOARDING_POINTS = 10
MIN_RECORD_WEIGHT = 50  # g
BASELINE_MIN = 300  # g
MIN_REDUCTION_PERCENT = 5  # %
MAX_WEEKLY_POINTS = 200


def calculate_weekly_points_logic(db: Session, user_id: int) -> Dict[str, Any]:
    # main-test 由来のロジックを採用
    last_week_grams, this_week_grams = get_last_two_weeks(db, user_id)
    
    # 改良版ベースライン計算：実際に記録がある週数に基づく
    # 過去の記録から実際にデータがある週数を計算
    from statistics import get_week_boundaries
    from datetime import datetime, timedelta
    
    current_week_start, _ = get_week_boundaries(datetime.now())
    
    # 過去8週間のデータを週別に集計して、実際に記録がある週を特定
    weekly_totals = []
    for weeks_back in range(2, 9):  # 先週から過去7週間（今週は除外）
        week_date = current_week_start - timedelta(weeks=weeks_back-1)
        week_total = get_total_grams_for_weeks(db, user_id, weeks_ago=weeks_back) - get_total_grams_for_weeks(db, user_id, weeks_ago=weeks_back-1)
        if week_total > 0:  # 記録がある週のみ
            weekly_totals.append(week_total)
    
    # ベースライン計算：記録がある週数に基づく
    if len(weekly_totals) >= 3:
        # 3週以上の記録がある場合：平均を使用
        baseline = sum(weekly_totals) / len(weekly_totals)
    elif len(weekly_totals) > 0:
        # 記録が1-2週の場合：先週比のみで評価（ベースライン比較をスキップ）
        baseline = 0.0  # ベースライン比較を無効にする
    else:
        # 記録がない場合：初回ユーザー扱い
        baseline = 0.0

    # 率計算（分母が0のときは特別扱い）
    if last_week_grams > 0:
        rate_last_week = (last_week_grams - this_week_grams) / last_week_grams
    else:
        rate_last_week = 0.0 if this_week_grams == 0 else -1.0

    if baseline > 0:
        rate_baseline = (baseline - this_week_grams) / baseline
    else:
        rate_baseline = 0.0 if this_week_grams == 0 else -1.0
    
    # 最終削減率の計算：ベースラインが0の場合は先週比のみで評価
    if baseline > 0:
        final_reduction_rate = min(rate_last_week, rate_baseline)
        comparison_method = f"先週比 vs ベースライン比({len(weekly_totals)}週平均)"
    else:
        final_reduction_rate = rate_last_week
        comparison_method = "先週比のみ(ベースライン不十分)"

    # --- Onboarding（初回）ルール（寛容） ---
    points_to_add = 0
    onboarding_applied = False
    # 初回判定: 先週のデータがなく、かつ過去データもない完全初回
    if last_week_grams == 0 and len(weekly_totals) == 0:
        # 初週扱い: 今週の記録が一定量を満たす場合は固定ポイントを付与
        if this_week_grams >= MIN_RECORD_WEIGHT:
            points_to_add = min(ONBOARDING_POINTS, MAX_WEEKLY_POINTS)
            onboarding_applied = True
    # 先週データはないが、過去データはある場合（ベースライン比のみで評価）
    elif last_week_grams == 0 and len(weekly_totals) > 0:
        if baseline > 0 and this_week_grams >= MIN_RECORD_WEIGHT:
            # ベースライン比のみで評価（先週比は除外）
            final_reduction_rate = rate_baseline
            comparison_method = f"ベースライン比のみ({len(weekly_totals)}週平均、先週データなし)"

    # --- 通常の削減評価 ---
    if not onboarding_applied:
        if final_reduction_rate > 0:
            reduction_percentage = int(final_reduction_rate * 100)
            # 最低削減率を下回る場合は付与なし
            if reduction_percentage >= MIN_REDUCTION_PERCENT:
                # 寛容モード: 最低閾値を満たせば最低1ポイント付与
                if reduction_percentage < 10:
                    calculated_points = 1
                else:
                    calculated_points = reduction_percentage // 10
                points_to_add = min(calculated_points, MAX_WEEKLY_POINTS)
            else:
                points_to_add = 0

    # --- idempotency: 同じ週に対する二重付与を防ぐ ---
    from statistics import get_week_boundaries
    from datetime import datetime

    today = datetime.now()
    week_start_dt, _ = get_week_boundaries(today)
    week_start_str = week_start_dt.strftime("%Y-%m-%d")

    user = db.get(User, user_id)
    if not user:
        return {
            "points_added": 0,
            "final_reduction_rate": round(final_reduction_rate * 100, 2),
            "rate_last_week": round(rate_last_week * 100, 2),
            "rate_baseline": round(rate_baseline * 100, 2),
            "message": "user_not_found",
        }

    # --- データ一貫性の自動修復 ---
    # ポイントが0なのに last_points_awarded_week_start が設定されている場合は不整合
    # ただし、実際に記録があり計算すべきポイントが存在する場合は修復対象
    if user.total_points == 0 and user.last_points_awarded_week_start is not None:
        # 実際に今週の記録があるか確認して、ポイント付与条件を満たしているかチェック
        if this_week_grams >= MIN_RECORD_WEIGHT and (last_week_grams == 0 and baseline == 0):
            # 条件を満たしているのにポイントが0 = 不整合なので修復
            user.last_points_awarded_week_start = None
            db.commit()
            print(f"[AUTO-REPAIR] User {user_id} ({user.username}): Cleared inconsistent last_points_awarded_week_start (has records but no points)")
        elif this_week_grams == 0:
            # 記録がないのに last_points_awarded_week_start が設定されている = 不整合
            user.last_points_awarded_week_start = None  
            db.commit()
            print(f"[AUTO-REPAIR] User {user_id} ({user.username}): Cleared inconsistent last_points_awarded_week_start (no records)")

    # すでにその週に付与済みかをチェック
    if user.last_points_awarded_week_start == week_start_str:
        return {
            "points_added": 0,
            "final_reduction_rate": round(final_reduction_rate * 100, 2),
            "rate_last_week": round(rate_last_week * 100, 2),
            "rate_baseline": round(rate_baseline * 100, 2),
            "message": "already_awarded",
            "week_start": week_start_str,
        }

    # 付与処理をトランザクション内で実施
    if points_to_add > 0:
        user.total_points += points_to_add

    # 処理を行ったことを示すため、付与が0でも週のフラグを更新する
    user.last_points_awarded_week_start = week_start_str
    db.commit()
    
    # 詳細情報をログ出力（app.pyで出力できるように詳細を返す）
    calculation_details = {
        "user_id": user_id,
        "last_week_grams": last_week_grams,
        "this_week_grams": this_week_grams,
        "baseline_grams": baseline,
        "baseline_weeks_count": len(weekly_totals) if 'weekly_totals' in locals() else 0,
        "comparison_method": comparison_method if 'comparison_method' in locals() else "unknown"
    }

    # --- 毎日最初の入力は必ず1ポイント付与 ---
    today_str = datetime.now().strftime('%Y-%m-%d')
    if user.last_points_awarded_date != today_str:
        user.total_points += 1
        user.last_points_awarded_date = today_str
        db.commit()
        # 既存ロジックのポイントと合算して返す
        calculation_details['daily_bonus'] = 1
        points_to_add += 1

    return {
        "points_added": points_to_add,
        "final_reduction_rate": round(final_reduction_rate * 100, 2),
        "rate_last_week": round(rate_last_week * 100, 2),
        "rate_baseline": round(rate_baseline * 100, 2),
        "week_start": week_start_str,
        "calculation_details": calculation_details,
        "onboarding_applied": onboarding_applied,
    }


def get_weekly_stats(db: Session, user_id: int, target_date: date) -> Dict[str, Any]:
    # target_date を calculate_weekly_statistics に渡す（APIの ?date= を反映する）
    return calculate_weekly_statistics(db, user_id, target_date)


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
            record_date=a_week_ago.isoformat(),
        ),
        FoodLossRecord(
            user_id=user_id,
            item_name="カレーの食べ残し",
            weight_grams=350.5,
            loss_reason_id=reason_eaten.id,
            record_date=a_week_ago.isoformat(),
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

# ---〇変更点---
# 残った食材をDBに登録する関数
def register_leftover_item(db: Session, user_id: int, item_name: str) -> int:
    new_suggest = arrange_suggest(
        user_id=user_id,
        item_name=item_name,
        arrange_recipe= generate_recipe_from_text(item_name)
    )
    db.add(new_suggest)
    db.commit()
    db.refresh(new_suggest)
    return new_suggest.id

# アレンジレシピのテキストを生成して返す関数
def get_arrange_recipe_text(item_name: str) -> str:
    # 現段階では固定のテンプレートまたは簡易的な応答を返します
    # 将来的にはここにAI APIなどの呼び出し処理を実装可能です
    return f"【{item_name}のアレンジレシピ提案】\n\n{item_name}を使った特製リメイク料理はいかがですか？\n細かく刻んでチャーハンに入れたり、卵とじにすると美味しくいただけます。\n味付けは醤油とみりんで和風にするのがおすすめです。"
# ---ここまで---