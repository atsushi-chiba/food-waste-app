# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, LossReason, FoodLossRecord
import os
import logging

logger = logging.getLogger(__name__)
import hashlib

# データベースファイルへのパスを定義
# os.path.dirname(__file__) は現在のファイルのディレクトリパス (例: C:/.../social-implementation/python)
# os.path.dirname(os.path.dirname(__file__)) で一つ上の親ディレクトリに移動
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///../db/food_loss.db")
# DATABASE_URLが環境変数にあればSupabase/PostgreSQLを使用、なければローカルSQLite
engine = create_engine(DATABASE_URL)

# データベースセッションを作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # PostgreSQL/Supabaseの場合はディレクトリ作成不要
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully!")

    db = SessionLocal()
    try:
        # 1. 初期廃棄理由の投入 (既存ロジック)
        if not db.query(LossReason).first():
            reasons = [
                LossReason(reason_text="期限切れ"),
                LossReason(reason_text="調理中の廃棄"),
                LossReason(reason_text="料理後の廃棄"),
                LossReason(reason_text="調理失敗"),
                LossReason(reason_text="その他"),
                LossReason(reason_text="食べ残し")
            ]
            db.add_all(reasons)
            db.commit()
            print("Loss reasons added.")
    except Exception as e:
        print(f"Error during init_db: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
