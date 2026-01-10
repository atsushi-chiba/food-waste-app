# 本番環境設定ガイド

## 1. 環境変数設定

本番環境では`.env`ファイルに以下の設定を行います：

```bash
# 基本設定
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-here-min-32-characters
DEBUG=False

# データベース（本番用PostgreSQL推奨）
DATABASE_URL=postgresql://user:password@localhost/social_implementation_prod

# OpenAI API
OPENAI_API_KEY=your-openai-api-key

# セキュリティ設定
SSL_DISABLE=False
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
CSRF_ENABLED=True

# ログ設定
LOG_LEVEL=INFO
LOG_FILE_PATH=/var/log/social-implementation/app.log

# 外部サービス（必要に応じて）
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
```

## 2. セキュリティ設定の適用

`app.py`にセキュリティ設定を追加：

```python
from security_config import SecurityConfig

app = Flask(__name__)

# 本番環境の場合のみセキュリティ設定を適用
if os.environ.get('FLASK_ENV') == 'production':
    SecurityConfig.configure_security(app)
```

## 3. データベース最適化

本番環境でのデータベース最適化を実行：

```python
from db_optimizer import DatabaseOptimizer

# バックアップ作成
DatabaseOptimizer.create_backup()

# インデックス最適化
DatabaseOptimizer.optimize_indexes()

# 統計情報更新
DatabaseOptimizer.update_statistics()
```

## 4. ログ設定

`production_logging.py`を使用してログ設定：

```python
from production_logging import setup_production_logging, setup_health_checks

# ログ設定
setup_production_logging(app)

# ヘルスチェック設定
setup_health_checks(app)
```

## 5. パフォーマンステスト

本番デプロイ前にパフォーマンステストを実行：

```python
from performance_test import PerformanceTest

# 負荷テスト実行
tester = PerformanceTest('https://your-production-domain.com')
tester.run_load_test()
```

## 6. デプロイメントスクリプト

### Gunicorn設定（gunicorn_config.py）

```python
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
preload_app = True

# ログ設定
accesslog = "/var/log/social-implementation/access.log"
errorlog = "/var/log/social-implementation/error.log"
loglevel = "info"
```

### Nginx設定例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/social-implementation/Static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## 7. Docker設定（推奨）

### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
```

### docker-compose.yml

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://user:password@db:5432/social_implementation_prod
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/var/log/social-implementation

  db:
    image: postgres:13
    environment:
      POSTGRES_DB: social_implementation_prod
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups

  redis:
    image: redis:6-alpine

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web

volumes:
  postgres_data:
```

## 8. デプロイメントコマンド

```bash
# 1. コードのデプロイ
git pull origin main

# 2. 依存関係の更新
pip install -r requirements.txt

# 3. データベースマイグレーション
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# 4. 静的ファイルの収集（必要に応じて）
# collectstatic

# 5. アプリケーションの再起動
sudo systemctl restart social-implementation
sudo systemctl restart nginx

# 6. ヘルスチェック
curl -f https://your-domain.com/health || exit 1
```

## 9. 監視設定

### systemd サービス設定

```ini
[Unit]
Description=Social Implementation Flask App
After=network.target

[Service]
Type=exec
User=appuser
Group=appuser
WorkingDirectory=/home/appuser/social-implementation
Environment=PATH=/home/appuser/social-implementation/venv/bin
ExecStart=/home/appuser/social-implementation/venv/bin/gunicorn --config gunicorn_config.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

## 10. バックアップ設定

### 自動バックアップスクリプト

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/home/appuser/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# データベースバックアップ
pg_dump social_implementation_prod > $BACKUP_DIR/db_backup_$DATE.sql

# アプリケーションファイルバックアップ
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz /home/appuser/social-implementation

# 古いバックアップの削除（30日以上古い）
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### crontab設定

```bash
# 毎日午前2時にバックアップ実行
0 2 * * * /home/appuser/backup.sh

# 毎週日曜日午前3時にデータベース最適化
0 3 * * 0 python /home/appuser/social-implementation/optimize_db.py
```