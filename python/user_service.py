# user_service.py
from sqlalchemy.orm import Session
from models import User, FoodLossRecord
import hashlib
from typing import Optional, Dict, Any

# --- ユーザー情報の取得 ---

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    ユーザー名でユーザーオブジェクトを取得する。（認証やログインチェック用）
    """
    return db.query(User).filter_by(username=username).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    IDでユーザーオブジェクトを取得する。（プロフィール表示やポイント更新時用）
    """
    return db.query(User).get(user_id)

def get_user_profile(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    """
    ユーザーIDから表示に必要な情報（ユーザー名、ポイントなど）を取得する。
    """
    user = db.query(User).filter_by(id=user_id).first()
    
    if user:
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "total_points": user.total_points,
            # 必要に応じて address や family_size などの情報を追加
        }
    return None


# --- ユーザーデータの作成と更新 ---

def register_new_user(db: Session, username: str, email: str, password: str) -> int:
    """
    新しいユーザーをデータベースに登録する。
    """
    # ユーザー名とメールアドレスの重複チェック
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        raise ValueError("ユーザー名またはメールアドレスは既に登録されています。")
    
    # パスワードをハッシュ化
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    new_user = User(
        username=username,
        email=email,
        password=hashed_password,
        total_points=0
        # address, family_size などがあればここに追加
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user.id

def update_user_points(db: Session, user_id: int, points_to_add: int) -> bool:
    """
    ユーザーの合計ポイントを更新する。
    """
    user = db.query(User).get(user_id)
    if user:
        user.total_points += points_to_add
        db.commit()
        return True
    return False