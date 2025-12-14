# auth_service.py
# (今回は使用しませんが、認証関連のロジックを置く場所として作成します)

# このファイルは、将来的にはログインロジック、ログアウトロジック、
# パスワード検証ロジックなどを一元管理する場所になります。
# 今は空のまま、または以下のダミー関数のみを置きます。

def check_password_hash(password: str, hashed_password: str) -> bool:
    """
    パスワードとハッシュ値を比較する（将来の機能）。
    """
    import hashlib
    input_hash = hashlib.sha256(password.encode()).hexdigest()
    return input_hash == hashed_password