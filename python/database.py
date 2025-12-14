# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, LossReason, FoodLossRecord
import os

# データベースファイルへのパスを定義
# os.path.dirname(__file__) は現在のファイルのディレクトリパス (例: C:/.../social-implementation/python)
# os.path.dirname(os.path.dirname(__file__)) で一つ上の親ディレクトリに移動
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(PROJECT_ROOT, 'db', 'food_loss.db')
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
    # データベースディレクトリが存在しなければ作成
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

    # 初期データを投入
    db = SessionLocal()
    try:
        # loss_reasonsテーブルに初期データがなければ追加
        if not db.query(LossReason).first():
            reasons = [
                LossReason(reason_text="期限切れ"),
                LossReason(reason_text="調理中の廃棄"),
                LossReason(reason_text="料理後の廃棄"),
                LossReason(reason_text="調理失敗"),
                LossReason(reason_text="その他")
            ]
            db.add_all(reasons)
            db.commit()
            print("Loss reasons added.")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()