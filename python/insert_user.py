# insert_test_data.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, LossReason, FoodLossRecord # 必要なモデルをインポート
import datetime
import hashlib
import logging
logger = logging.getLogger(__name__) 

# --- データベース接続設定 (database.pyと同じロジックを使用) ---
# os.path.dirname(__file__) は現在のファイルのディレクトリ (例: C:/.../social-implementation/python)
# os.path.dirname(os.path.dirname(__file__)) で一つ上の親ディレクトリ (例: C:/.../social-implementation) に移動
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(PROJECT_ROOT, 'db', 'food_loss.db')
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# データベースエンジンとセッションを作成
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def add_test_data():
    session = Session()
    try:
        # 1. ユーザーの取得または作成 (今回は既存の'test_user'を使用)
        test_user = session.query(User).filter_by(username="test_user").first()
        
        if not test_user:
            # もしユーザーが存在しなければ新規作成
            hashed_password = hashlib.sha256("testpass".encode()).hexdigest()
            test_user = User(
                username="test_user", 
                password=hashed_password, 
                email="test@example.com"
            )
            session.add(test_user)
            session.commit()
            logger.info("Test user created.")

        # 2. 廃棄理由（「期限切れ」）のIDを取得
        # ※ init_db()で初期データが投入されていることを前提とします
        expired_reason = session.query(LossReason).filter_by(reason_text="期限切れ").first()
        eaten_reason = session.query(LossReason).filter_by(reason_text="食べ残し").first()
        
        if not expired_reason or not eaten_reason:
            logger.error("Error: Loss reasons not found. Please run database initialization.")
            return

        # 3. 新しいフードロス記録を作成
        record1 = FoodLossRecord(
            user_id=test_user.id,
            item_name="牛乳 (期限切れ)",
            weight_grams=1000.0,
            loss_reason_id=expired_reason.id
            # record_dateはモデルのdefault設定により自動挿入される
        )
        
        record2 = FoodLossRecord(
            user_id=test_user.id,
            item_name="カレーの食べ残し",
            weight_grams=350.5,
            loss_reason_id=eaten_reason.id
        )

        # 4. セッションに追加し、コミット
        session.add_all([record1, record2])
        session.commit()
        logger.info("Food loss test data added successfully for test_user!")
        
    except Exception as e:
        session.rollback()
        print(f"Error adding test data: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    add_test_data()