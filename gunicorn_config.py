# Gunicorn設定ファイル
import multiprocessing
import os

# 基本設定
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000

# パフォーマンス設定
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
preload_app = True

# ログ設定
log_dir = os.environ.get('LOG_DIR', '/var/log/social-implementation')
accesslog = f"{log_dir}/access.log"
errorlog = f"{log_dir}/error.log"
loglevel = os.environ.get('LOG_LEVEL', 'info')

# セキュリティ設定
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# プロセス管理
user = os.environ.get('APP_USER', 'appuser')
group = os.environ.get('APP_GROUP', 'appuser')
tmp_upload_dir = None
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# 開発環境での設定調整
if os.environ.get('FLASK_ENV') == 'development':
    reload = True
    reload_extra_files = ['templates/', 'Static/']
    workers = 1