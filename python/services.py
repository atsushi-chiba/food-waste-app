from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, FoodLossRecord, LossReason
from schemas import LossRecordInput
import hashlib
from datetime import datetime, timedelta, date, time
from typing import Dict, Any, List, Optional, Tuple
from statistics import (
    get_week_boundaries,
    get_total_grams_for_week,
    get_total_grams_for_weeks,
    # target_date.weekday() は月曜(0)から日曜(6)

def get_start_and_end_of_week(target_date: date) -> Tuple[date, date]:
    """与えられた日付を含む週の日曜と土曜を返す (日曜日を週の始まりとする)。"""
    start_of_week = target_date - timedelta(days=(target_date.weekday() + 1) % 7)
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week, end_of_week


def get_weekly_stats(db: Session, user_id: int, target_date: date) -> Dict[str, Any]:
    """
    指定された日付を含む週の統計データ（グラフ用、表用）を取得し、JSが期待する形式に整形する。
    """
    # target_dateから週の始まりと終わり（日曜〜土曜）を計算
    date_start_of_week, date_end_of_week = get_start_and_end_of_week(target_date)

    # 1. データベースクエリ用のISO文字列境界を作成
    datetime_start = datetime.combine(date_start_of_week, time.min)
    datetime_end = datetime.combine(date_end_of_week, time.max)
    start_str = datetime_start.isoformat()
    end_str = datetime_end.isoformat()

    # 2. 週間記録を全て取得（文字列のISO範囲で比較）
    records = db.query(FoodLossRecord, LossReason.reason_text) \
        .join(LossReason) \
        .filter(
            FoodLossRecord.user_id == user_id,
            FoodLossRecord.record_date.between(start_str, end_str)
        ) \
        .order_by(FoodLossRecord.record_date) \
        .all()
    rate_baseline = 0.0
    
    # a. 先週比の削減率を計算
    if last_week_grams > 0:
        rate_last_week = (last_week_grams - this_week_grams) / last_week_grams
    else:
        rate_last_week = 0.0 if this_week_grams == 0 else -1.0 


    # b. ベースライン（平均）比の削減率を計算
    if base_line_grams > 0:
        rate_baseline = (base_line_grams - this_week_grams) / base_line_grams

    
    # --- 3. 最終的な削減率とポイントの決定 ---
    
    final_reduction_rate = min(rate_last_week, rate_baseline)
    
    if final_reduction_rate > 0:
        reduction_percentage = int(final_reduction_rate * 100)
        calculated_points = reduction_percentage // 10
        points_to_add = min(calculated_points, 100)

    # 4. ポイントをデータベースに更新
    user = db.query(User).get(user_id)
    if user:
        user.total_points += points_to_add
        db.commit() 
        
    return {
        "points_added": points_to_add,
        "final_reduction_rate": round(final_reduction_rate * 100, 2),
        "rate_last_week": round(rate_last_week * 100, 2),
        "rate_baseline": round(base_line_grams / (1 if base_line_grams == 0 else base_line_grams) * 100, 2) # rate_baselineの表示を修正
    }
def get_all_loss_reasons(db: Session) -> List[str]:
    """
    データベースに登録されている全ての廃棄理由のテキストをリストで取得する。
    """
    # LossReasonモデルから reason_text の値のみをすべて取得
    reasons = db.query(LossReason.reason_text).order_by(LossReason.id).all()
    
    # [('理由1',), ('理由2',)...] -> ['理由1', '理由2', ...] の形式に変換
    return [r[0] for r in reasons]

def get_user_profile(db: Session, user_id: int) -> Dict[str, Any] | None:
    """
    ユーザーIDから表示に必要な情報（ユーザー名、ポイント）を取得する。
    """
    user = db.query(User).filter_by(id=user_id).first()
    
    if user:
        return {
            "user_id": user.id,
            "username": user.username,
            "total_points": user.total_points,
            # ここに必要に応じて address, family_size などの情報を追加
        }
    return None

def add_new_loss_record_direct(db: Session, record_data: Dict[str, Any]) -> int:
    """
    検証済みの廃棄記録データ（辞書形式）をデータベースに挿入する純粋なロジック。
    
    Args:
        db: データベースセッション
        record_data: 必須項目を含み、型チェック済みのクリーンなデータ辞書
        
    Returns:
        挿入されたレコードのID
    """
    
    # 1. 外部キー（LossReason）の存在チェックとID取得
    # このチェックは、データがDBに存在する理由テキストを参照しているか確認するために必要
    reason = db.query(LossReason).filter_by(reason_text=record_data['reason_text']).first()
    
    if not reason:
        # 理由が見つからない場合、外部キー制約違反になるため、エラーを発生させる
        raise ValueError(f"無効な廃棄理由: {record_data['reason_text']}")

    # 2. データベースへの挿入（SQLAlchemyモデルのインスタンス化）
    new_record = FoodLossRecord(
        user_id=record_data['user_id'],
        item_name=record_data['item_name'],
        weight_grams=record_data['weight_grams'],
        loss_reason_id=reason.id, # 外部キーIDを使用
        # record_date は models.py の設定により自動挿入される
    )
    
    db.add(new_record)
    db.commit() # 変更を永続化
    db.refresh(new_record) # 挿入されたレコードのIDなどを取得
    
    return new_record.id

def get_start_and_end_of_week(target_date: datetime.date) -> Tuple[datetime.date, datetime.date]:
    """与えられた日付を含む週の日曜と土曜を返す (日曜日を週の始まりとする)。"""
    # target_date.weekday() は月曜(0)から日曜(6)
    start_of_week = target_date - timedelta(days=(target_date.weekday() + 1) % 7)
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week, end_of_week

def get_start_and_end_of_week(target_date: date) -> Tuple[date, date]:
    """与えられた日付を含む週の日曜と土曜を返す (日曜日を週の始まりとする)。"""
    # target_date.weekday() は月曜(0)から日曜(6)
    start_of_week = target_date - timedelta(days=(target_date.weekday() + 1) % 7)
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week, end_of_week

def get_weekly_stats(db: Session, user_id: int, target_date: date) -> Dict[str, Any]:
    """
    指定された日付を含む週の統計データ（グラフ用、表用）を取得し、JSが期待する形式に整形する。
    """
    # target_dateから週の始まりと終わり（日曜〜土曜）を計算
    date_start_of_week, date_end_of_week = get_start_and_end_of_week(target_date)

    # 1. データベースクエリ用のISO文字列境界を作成
    datetime_start = datetime.combine(date_start_of_week, time.min)
    datetime_end = datetime.combine(date_end_of_week, time.max)
    
    start_str = datetime_start.isoformat()
    end_str = datetime_end.isoformat()
    
    # 2. 週間記録を全て取得
    records = db.query(FoodLossRecord, LossReason.reason_text) \
        .join(LossReason) \
        .filter(
            FoodLossRecord.user_id == user_id,
            # ISO文字列で比較することで、範囲内の全てのタイムスタンプを捕捉
            FoodLossRecord.record_date.between(start_str, end_str) 
        ) \
        .order_by(FoodLossRecord.record_date) \
        .all()
        
    # 2-b. 週間廃棄品目一覧のデータを作成 (テーブル用)
    dish_table_data = [
        {
            # 日付を 'MM/DD' 形式に変換
            "date": datetime.fromisoformat(rec.FoodLossRecord.record_date).strftime('%m/%d'),
            "dish_name": rec.FoodLossRecord.item_name,
            # 小数点以下1桁に丸める
            "weight_grams": round(rec.FoodLossRecord.weight_grams, 1), 
            "reason": rec.reason_text
        }
        for rec in records
    ]
    
    # --- 3. 日別合計グラム数を計算 (Pythonで集計) ---
    # キー: YYYY-MM-DD
    daily_grams_aggregation = {}
    for rec in records:
        # レコードの日付部分を取得
        record_date = datetime.fromisoformat(rec.FoodLossRecord.record_date).date()
        date_str = record_date.strftime('%Y-%m-%d')
        grams = rec.FoodLossRecord.weight_grams
        
        daily_grams_aggregation[date_str] = daily_grams_aggregation.get(date_str, 0.0) + grams
        
    # --- 4. 全曜日をカバーし、グラフデータを作成 (日曜始まりで順序を保証) ---
    daily_graph_data = []
    jp_weekdays = ["日", "月", "火", "水", "木", "金", "土"]
    current_date = date_start_of_week # 日曜日から開始
    for i in range(7):
        date_str = current_date.strftime('%Y-%m-%d')
        # i=0が日曜日、i=6が土曜日
        day_name = jp_weekdays[i]
        
        # 該当日の合計を取得（データがなければ 0.0）
        grams = round(daily_grams_aggregation.get(date_str, 0.0), 1)
        
        daily_graph_data.append({
            "day": day_name, 
            "total_grams": grams
        })
        current_date += timedelta(days=1) # 次の日へ
    
    # 5. 最終的なレスポンス形式に整形
    is_data_present = len(records) > 0

    return {
        "is_data_present": is_data_present,
        "week_start": date_start_of_week.strftime('%Y-%m-%d'),
        "daily_graph_data": daily_graph_data,
        "dish_table": dish_table_data
    }

def add_test_loss_records(db: Session, user_id: int) -> bool:
    """
    ユーザーのフードロス記録がまだ存在しない場合、テストデータを挿入する。
    """
    # 既にレコードが存在するかチェックし、存在する場合は挿入をスキップ
    if db.query(FoodLossRecord).filter_by(user_id=user_id).first():
        print(f"User {user_id} already has records. Skipping test data insertion.")
        return False
    
    # LossReasonのIDを取得
    # NOTE: database.pyのinit_db()で以下の理由が投入されていることを前提とする
    reason_expired = db.query(LossReason).filter_by(reason_text="期限切れ").first()
    reason_eaten = db.query(LossReason).filter_by(reason_text="料理後の廃棄").first()
    
    if not reason_expired or not reason_eaten:
        print("Error: Loss reasons not found. Cannot insert test data.")
        return False
        
    # テストデータを挿入する日付を決定
    today = datetime.now()
    # 記録を過去の任意の日付（例：5日前と3日前）で作成し、今週の統計に反映されるようにする
    a_week_ago = today - timedelta(days=7)

    records = [
        FoodLossRecord(
            user_id=user_id,
            item_name="牛乳 (期限切れ)",
            weight_grams=1000.0,
            loss_reason_id=reason_expired.id,
            # ISOフォーマット文字列に変換して挿入
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
    print(f"Inserted {len(records)} test records for user {user_id}.")
    return True
