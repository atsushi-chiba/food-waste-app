# statistics.py (修正案)
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import FoodLossRecord, LossReason  # models.pyからインポート


# --- 1. 週の境界計算ヘルパー (そのまま残す) ---
def get_week_boundaries(today: datetime) -> tuple[datetime, datetime]:
    """
    指定された日付を含む「月曜日から日曜日まで」の一週間の境界を計算する。
    """
    # 0=月曜日, 6=日曜日
    days_to_monday = today.weekday()
    # ... (ロジックは省略) ...
    start_of_week = today - timedelta(days=days_to_monday)
    monday = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6)
    end_of_week = sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
    return monday, end_of_week


# --- 2. 汎用的な期間の合計取得ヘルパー (Services層で使用) ---
def get_total_grams_for_week(
    db: Session, user_id: int, start_date: datetime, end_date: datetime
) -> float:
    """
    指定された「月〜日」の一週間の合計廃棄重量を取得する。（ポイント計算用）
    """
    # データベースのレコード日付は文字列（ISO 8601）として保存されているため、文字列形式に変換
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    total_grams = (
        db.query(func.sum(FoodLossRecord.weight_grams))
        .filter(FoodLossRecord.user_id == user_id)
        .filter(FoodLossRecord.record_date >= start_str)
        .filter(FoodLossRecord.record_date <= end_str)
        .scalar()
    )

    return total_grams or 0.0


def get_last_two_week_ranges(today: datetime) -> Dict[str, tuple[datetime, datetime]]:
    """
    指定された日付を基準に、「今週」と「先週」の厳密な月曜日の開始と日曜日の終了時刻を計算する。
    """
    # 1. 今週の月曜日を正確に計算する (月曜日=0, 日曜日=6)
    days_since_monday = today.weekday()

    # 今週の月曜日 00:00:00
    this_monday = (today - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # 今週の日曜日 23:59:59
    this_sunday = (this_monday + timedelta(days=6)).replace(
        hour=23, minute=59, second=59, microsecond=999999
    )

    # 2. 先週の境界を計算
    last_monday = this_monday - timedelta(weeks=1)
    last_sunday = this_sunday - timedelta(weeks=1)

    return {
        "this_week": (this_monday, this_sunday),
        "last_week": (last_monday, last_sunday),
    }


def calculate_weekly_statistics(
    db: Session, user_id: int, target_date: datetime = None
) -> Dict[str, Any]:
    """
    指定した日付を含む「日曜始まり〜土曜終わり」の一週間について、
    廃棄された料理名リストと日別合計重量を計算する。
    """

    if target_date is None:
        target_date = datetime.now()

    # target_date が date の場合は datetime に変換しておく
    if not isinstance(target_date, datetime):
        target_date = datetime(target_date.year, target_date.month, target_date.day)

    # app.py の表示ロジックに合わせて「日曜始まり」にする
    # app.py: start_of_week = target_date - timedelta(days=(target_date.weekday() + 1) % 7)
    start_of_week = target_date - timedelta(days=(target_date.weekday() + 1) % 7)
    # 週の開始（0:00）と終了（23:59:59.999999）を作る
    week_start = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = (week_start + timedelta(days=6)).replace(
        hour=23, minute=59, second=59, microsecond=999999
    )

    # データベースのレコード日付は文字列（ISO 8601）として保存されているため、文字列形式に変換
    week_start_str = week_start.isoformat()
    week_end_str = week_end.isoformat()

    # 1. 週間の全記録を取得 (日付フィルター)
    weekly_records = (
        db.query(FoodLossRecord)
        .filter(FoodLossRecord.user_id == user_id)
        .filter(FoodLossRecord.record_date >= week_start_str)
        .filter(FoodLossRecord.record_date <= week_end_str)
        .all()
    )

    if not weekly_records:
        return {
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "is_data_present": False,
            "dish_table": [],
            "daily_graph_data": [],
        }

    # 2. 廃棄された料理名リスト (表データ) の作成
    # 料理名と廃棄量、理由のリストを作成
    dish_table_data = []
    for record in weekly_records:
        reason_text = (
            db.query(LossReason.reason_text)
            .filter(LossReason.id == record.loss_reason_id)
            .scalar()
        )

        dish_table_data.append(
            {
                "id": record.id,
                "dish_name": record.item_name,
                "weight_grams": round(record.weight_grams, 1),
                "reason": reason_text if reason_text else "不明",
                "date": record.record_date[:10],  # 日付部分 'YYYY-MM-DD' のみ抽出
            }
        )

    # 3. 日別合計重量 (棒グラフデータ) の計算

    # SQLで日付ごとに合計重量を集計
    daily_summary = (
        db.query(
            func.substr(FoodLossRecord.record_date, 1, 10).label("date"),
            func.sum(FoodLossRecord.weight_grams).label("total_grams"),
        )
        .filter(FoodLossRecord.user_id == user_id)
        .filter(FoodLossRecord.record_date >= week_start_str)
        .filter(FoodLossRecord.record_date <= week_end_str)
        .group_by(func.substr(FoodLossRecord.record_date, 1, 10))
        .order_by("date")
        .all()
    )

    # 全曜日をカバーし、データがない日は 0 にする
    daily_graph_data = []
    current_date = week_start
    for i in range(7):
        date_str = current_date.strftime("%Y-%m-%d")
        grams = 0.0

        # 集計結果から該当日のデータを探す
        for row in daily_summary:
            if row.date == date_str:
                grams = round(row.total_grams, 1)
                break

        daily_graph_data.append(
            {
                "day": current_date.strftime("%a"),  # 曜日名 (例: Mon, Tue)
                "date": date_str,
                "total_grams": grams,
            }
        )
        current_date += timedelta(days=1)

    return {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
        "is_data_present": True,
        "dish_table": dish_table_data,
        "daily_graph_data": daily_graph_data,
    }


def get_total_grams_for_weeks(db: Session, user_id: int, weeks_ago: int) -> float:
    """
    過去 N 週間分の合計廃棄重量（グラム）を取得する。
    （weeks_ago=4なら、今週を含まない過去4週間を取得）
    """
    today = datetime.now()

    # 過去 N 週間の起点となる日時を計算
    # 例: 4週間前は today - 4週間
    start_point = today - timedelta(weeks=weeks_ago)

    # データベースのレコード日付は文字列（ISO 8601）
    start_str = start_point.isoformat()

    total_grams = (
        db.query(func.sum(FoodLossRecord.weight_grams))
        .filter(FoodLossRecord.user_id == user_id)
        .filter(FoodLossRecord.record_date >= start_str)
        .filter(FoodLossRecord.record_date < today.isoformat())
        .scalar()
    )

    return total_grams or 0.0


def get_last_two_weeks(db: Session, user_id: int) -> tuple[float, float]:
    """
    直近の2週間分の合計廃棄重量（グラム）を取得する。
    戻り値は (先週の合計, 今週の合計) のタプル。
    """
    today = datetime.now()

    # 今週の月曜日と日曜日を取得
    this_monday, this_sunday = get_week_boundaries(today)

    # 先週の月曜日と日曜日を計算
    last_monday = this_monday - timedelta(weeks=1)
    last_sunday = this_sunday - timedelta(weeks=1)

    # record_dateの型を統一して比較（datetimeとstrの両方に対応）
    # 先週の合計重量を取得
    last_week_records = db.query(FoodLossRecord).filter(
        FoodLossRecord.user_id == user_id
    ).all()
    
    last_week_grams = 0.0
    this_week_grams = 0.0
    
    for record in last_week_records:
        # record_dateをdatetimeに変換
        if isinstance(record.record_date, str):
            record_dt = datetime.fromisoformat(record.record_date.replace('T', ' '))
        else:
            record_dt = record.record_date
            
        # 週の境界をチェック
        if last_monday <= record_dt <= last_sunday:
            last_week_grams += record.weight_grams
        elif this_monday <= record_dt <= this_sunday:
            this_week_grams += record.weight_grams

    return last_week_grams, this_week_grams
