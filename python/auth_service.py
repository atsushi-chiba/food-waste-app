# auth_service.py
# 認証関連のロジックを一元管理

import hashlib
import secrets
from typing import Optional


def generate_password_hash(password: str) -> str:
    """
    パスワードをハッシュ化する（SHA256 + ランダムソルト）
    学校用設定では簡単な実装を使用
    """
    # ランダムソルト生成
    salt = secrets.token_hex(16)
    # パスワード + ソルトをハッシュ化
    password_with_salt = password + salt
    password_hash = hashlib.sha256(password_with_salt.encode()).hexdigest()
    # ソルト + ハッシュの形式で保存
    return salt + ":" + password_hash


def check_password_hash(password: str, stored_hash: str) -> bool:
    """
    パスワードとハッシュ値を比較する
    """
    try:
        # 保存されたハッシュからソルトとハッシュを分離
        if ":" not in stored_hash:
            # 古い形式のハッシュ（ソルトなし）をサポート
            input_hash = hashlib.sha256(password.encode()).hexdigest()
            return input_hash == stored_hash
        
        salt, expected_hash = stored_hash.split(":", 1)
        # 入力パスワード + ソルトでハッシュ作成
        password_with_salt = password + salt
        input_hash = hashlib.sha256(password_with_salt.encode()).hexdigest()
        return input_hash == expected_hash
    
    except Exception:
        return False


def verify_login(username: str, password: str, user_password_hash: str) -> bool:
    """
    ログイン認証を行う
    """
    if not username or not password:
        return False
    
    return check_password_hash(password, user_password_hash)
