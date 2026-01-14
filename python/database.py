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
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(PROJECT_ROOT, "db", "food_loss.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# データベースエンジンを作成
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
    # データベースディレクトリの作成
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully!")

    # --- 既存 DB に新しい列がなければ追加（軽いマイグレーション） ---
    # SQLite では ALTER TABLE ADD COLUMN が使えるため、存在確認してから追加する
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("users")]
    if "last_points_awarded_week_start" not in columns:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN last_points_awarded_week_start VARCHAR(10)"
                )
            )
            logger.info("Added column users.last_points_awarded_week_start")

    if "last_points_awarded_date" not in columns:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN last_points_awarded_date VARCHAR(10)"
                )
            )
            logger.info("Added column users.last_points_awarded_date")

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
                LossReason(reason_text="食べ残し") # insert_user.pyで使われていたので追加を推奨
            ]
            db.add_all(reasons)
            db.commit()
            print("Loss reasons added.")

        # 2. テストユーザーの投入 (追加ロジック)
            
    except Exception as e:
        print(f"Error during init_db: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
