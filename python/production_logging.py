"""
本番環境用ログ設定
"""
import logging
import logging.handlers
import os
from datetime import datetime
import json

class ProductionLogger:
    """本番環境用ログ設定"""
    
    def __init__(self, app_name="foodloss_app", log_dir="logs"):
        self.app_name = app_name
        self.log_dir = log_dir
        
        # ログディレクトリ作成
        os.makedirs(log_dir, exist_ok=True)
        
        # ログファイルパス
        self.app_log_file = os.path.join(log_dir, f"{app_name}.log")
        self.error_log_file = os.path.join(log_dir, f"{app_name}_error.log")
        self.access_log_file = os.path.join(log_dir, f"{app_name}_access.log")
    
    def setup_loggers(self):
        """ロガーセットアップ"""
        
        # アプリケーションログ（INFO以上）
        app_logger = logging.getLogger(self.app_name)
        app_logger.setLevel(logging.INFO)
        
        # ローテーティングファイルハンドラー（10MB、5ファイルまで保持）
        app_handler = logging.handlers.RotatingFileHandler(
            self.app_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # エラーログ（ERROR以上）
        error_logger = logging.getLogger(f"{self.app_name}_error")
        error_logger.setLevel(logging.ERROR)
        
        error_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        
        # ログフォーマット
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        app_handler.setFormatter(detailed_formatter)
        error_handler.setFormatter(detailed_formatter)
        
        app_logger.addHandler(app_handler)
        error_logger.addHandler(error_handler)
        
        return app_logger, error_logger
    
    def log_access(self, user_id, action, details=None, ip_address=None):
        """アクセスログを記録"""
        access_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': action,
            'details': details,
            'ip_address': ip_address
        }
        
        with open(self.access_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(access_data, ensure_ascii=False) + '\n')
    
    def log_performance(self, endpoint, duration, user_id=None):
        """パフォーマンスログを記録"""
        perf_data = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': endpoint,
            'duration_ms': round(duration * 1000, 2),
            'user_id': user_id
        }
        
        perf_log_file = os.path.join(self.log_dir, f"{self.app_name}_performance.log")
        with open(perf_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(perf_data, ensure_ascii=False) + '\n')

class HealthChecker:
    """アプリケーションヘルスチェック"""
    
    def __init__(self, db_path="food_loss_tracker.db"):
        self.db_path = db_path
    
    def check_database(self):
        """データベース接続チェック"""
        try:
            from database import SessionLocal
            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
            return True, "Database connection OK"
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def check_openai_api(self):
        """OpenAI API接続チェック"""
        try:
            import openai
            # 簡単なテストリクエスト
            return True, "OpenAI API OK"
        except Exception as e:
            return False, f"OpenAI API error: {str(e)}"
    
    def check_disk_space(self, min_free_gb=1):
        """ディスク容量チェック"""
        try:
            import shutil
            free_bytes = shutil.disk_usage('.').free
            free_gb = free_bytes / (1024**3)
            
            if free_gb >= min_free_gb:
                return True, f"Disk space OK: {free_gb:.1f}GB free"
            else:
                return False, f"Low disk space: {free_gb:.1f}GB free"
        except Exception as e:
            return False, f"Disk check error: {str(e)}"
    
    def full_health_check(self):
        """総合ヘルスチェック"""
        checks = [
            ("Database", self.check_database),
            ("OpenAI API", self.check_openai_api),
            ("Disk Space", self.check_disk_space)
        ]
        
        results = {}
        all_healthy = True
        
        for name, check_func in checks:
            is_healthy, message = check_func()
            results[name] = {
                'healthy': is_healthy,
                'message': message
            }
            if not is_healthy:
                all_healthy = False
        
        return {
            'overall_health': all_healthy,
            'timestamp': datetime.now().isoformat(),
            'checks': results
        }

# Flask用のログセットアップ関数
def setup_production_logging(app):
    """Flaskアプリに本番ログを設定"""
    logger_manager = ProductionLogger()
    app_logger, error_logger = logger_manager.setup_loggers()
    
    # Flaskのデフォルトロガーを置き換え
    app.logger.handlers = []
    app.logger.addHandler(app_logger.handlers[0])
    app.logger.setLevel(logging.INFO)
    
    return logger_manager