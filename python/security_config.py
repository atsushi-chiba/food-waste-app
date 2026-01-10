"""
本番環境用セキュリティ設定
"""
import os
from datetime import timedelta

class SecurityConfig:
    """セキュリティ設定クラス"""
    
    # セッションセキュリティ（開発環境テスト用）
    SESSION_COOKIE_SECURE = False  # 開発環境ではHTTP接続のため無効
    SESSION_COOKIE_HTTPONLY = True  # XSS攻撃を防ぐ
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF攻撃を防ぐ
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)  # セッション有効期限
    
    # CSRFプロテクション
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # パスワード設定（将来的にユーザー認証を強化する場合）
    MIN_PASSWORD_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_NUMBERS = True
    REQUIRE_SPECIAL_CHARS = True
    
    # レート制限（API呼び出し制限）
    RATE_LIMIT_PER_MINUTE = 60
    RATE_LIMIT_PER_HOUR = 1000
    
    # ファイルアップロード制限
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'txt', 'csv'}
    
    # SQLインジェクション対策
    SQL_QUERY_TIMEOUT = 30  # 秒
    
    # セキュリティヘッダー
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    }

    @classmethod
    def configure_security(cls, app):
        """Flaskアプリケーションに全セキュリティ設定を適用"""
        # セッション設定
        app.config.update({
            'SESSION_COOKIE_SECURE': cls.SESSION_COOKIE_SECURE,
            'SESSION_COOKIE_HTTPONLY': cls.SESSION_COOKIE_HTTPONLY,
            'SESSION_COOKIE_SAMESITE': cls.SESSION_COOKIE_SAMESITE,
            'PERMANENT_SESSION_LIFETIME': cls.PERMANENT_SESSION_LIFETIME,
            'WTF_CSRF_ENABLED': cls.WTF_CSRF_ENABLED,
            'WTF_CSRF_TIME_LIMIT': cls.WTF_CSRF_TIME_LIMIT,
            'MAX_CONTENT_LENGTH': cls.MAX_CONTENT_LENGTH
        })
        
        # セキュリティヘッダーの適用
        apply_security_headers(app)
        
        return app

def apply_security_headers(app):
    """Flaskアプリにセキュリティヘッダーを適用"""
    @app.after_request
    def add_security_headers(response):
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
    
    return app