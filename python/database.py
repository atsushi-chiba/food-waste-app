# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, LossReason, FoodLossRecord
import os
import hashlib

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
    # データベースディレクトリの作成
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

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
        if not db.query(User).filter_by(username="a").first():
            hashed_password = hashlib.sha256("testpass".encode()).hexdigest() #
            test_user = User(
                username="a", 
                password=hashed_password, 
                email="a@a"
            )
            db.add(test_user)
            db.commit()
            print("Test user 'a' created automatically.")
            
    except Exception as e:
        print(f"Error during init_db: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()