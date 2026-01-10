# 本番環境デプロイメントスクリプト
import os
import subprocess
import sys
import logging
from pathlib import Path

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeploymentManager:
    def __init__(self, app_dir="/home/appuser/social-implementation"):
        self.app_dir = Path(app_dir)
        self.venv_dir = self.app_dir / "venv"
        self.backup_dir = Path("/home/appuser/backups")
        
    def run_command(self, command, check=True, shell=True):
        """コマンドを実行してログに記録"""
        logger.info(f"実行中: {command}")
        result = subprocess.run(command, shell=shell, capture_output=True, text=True)
        
        if result.stdout:
            logger.info(f"出力: {result.stdout}")
        if result.stderr:
            logger.warning(f"エラー: {result.stderr}")
            
        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, command)
            
        return result
    
    def backup_database(self):
        """データベースをバックアップ"""
        logger.info("データベースバックアップを開始")
        
        timestamp = subprocess.check_output("date +%Y%m%d_%H%M%S", shell=True, text=True).strip()
        backup_file = self.backup_dir / f"db_backup_before_deploy_{timestamp}.sql"
        
        # PostgreSQLの場合
        if os.environ.get('DATABASE_URL', '').startswith('postgresql'):
            db_url = os.environ.get('DATABASE_URL')
            self.run_command(f"pg_dump '{db_url}' > {backup_file}")
        # SQLiteの場合
        else:
            db_file = self.app_dir / "database.db"
            if db_file.exists():
                self.run_command(f"cp {db_file} {backup_file.with_suffix('.db')}")
                
        logger.info(f"データベースバックアップ完了: {backup_file}")
    
    def backup_application(self):
        """アプリケーションファイルをバックアップ"""
        logger.info("アプリケーションバックアップを開始")
        
        timestamp = subprocess.check_output("date +%Y%m%d_%H%M%S", shell=True, text=True).strip()
        backup_file = self.backup_dir / f"app_backup_before_deploy_{timestamp}.tar.gz"
        
        # 重要なファイルのみバックアップ（venvは除外）
        self.run_command(f"tar --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' -czf {backup_file} -C {self.app_dir.parent} {self.app_dir.name}")
        
        logger.info(f"アプリケーションバックアップ完了: {backup_file}")
    
    def update_code(self, branch="main"):
        """コードを最新版に更新"""
        logger.info("コードの更新を開始")
        
        os.chdir(self.app_dir)
        
        # Gitリポジトリの確認
        self.run_command("git status")
        
        # 変更のプル
        self.run_command(f"git pull origin {branch}")
        
        logger.info("コード更新完了")
    
    def update_dependencies(self):
        """依存関係を更新"""
        logger.info("依存関係の更新を開始")
        
        pip_cmd = f"{self.venv_dir}/bin/pip"
        requirements_file = self.app_dir / "requirements.txt"
        
        if requirements_file.exists():
            self.run_command(f"{pip_cmd} install -r {requirements_file}")
        else:
            logger.warning("requirements.txtが見つかりません")
            
        logger.info("依存関係更新完了")
    
    def run_database_migrations(self):
        """データベースマイグレーションを実行"""
        logger.info("データベースマイグレーションを開始")
        
        python_cmd = f"{self.venv_dir}/bin/python"
        
        # テーブル作成/更新
        migration_script = """
from app import app, db
app.app_context().push()
db.create_all()
print("データベース更新完了")
"""
        
        self.run_command(f"echo '{migration_script}' | {python_cmd}")
        
        logger.info("データベースマイグレーション完了")
    
    def optimize_database(self):
        """データベースを最適化"""
        logger.info("データベース最適化を開始")
        
        python_cmd = f"{self.venv_dir}/bin/python"
        
        optimization_script = """
from db_optimizer import DatabaseOptimizer
try:
    DatabaseOptimizer.optimize_indexes()
    DatabaseOptimizer.update_statistics()
    print("データベース最適化完了")
except Exception as e:
    print(f"最適化エラー: {e}")
"""
        
        self.run_command(f"echo '{optimization_script}' | {python_cmd}")
        
        logger.info("データベース最適化完了")
    
    def restart_application(self):
        """アプリケーションを再起動"""
        logger.info("アプリケーション再起動を開始")
        
        # systemdサービスの再起動
        self.run_command("sudo systemctl restart social-implementation")
        
        # Nginxの再起動（設定変更がある場合）
        self.run_command("sudo systemctl restart nginx")
        
        logger.info("アプリケーション再起動完了")
    
    def health_check(self, url="http://localhost:8000/health", max_attempts=5):
        """ヘルスチェックを実行"""
        logger.info("ヘルスチェックを開始")
        
        import time
        
        for attempt in range(max_attempts):
            try:
                result = self.run_command(f"curl -f {url}", check=False)
                if result.returncode == 0:
                    logger.info("ヘルスチェック成功")
                    return True
                else:
                    logger.warning(f"ヘルスチェック失敗 (試行 {attempt + 1}/{max_attempts})")
                    time.sleep(10)
            except Exception as e:
                logger.warning(f"ヘルスチェックエラー: {e}")
                time.sleep(10)
        
        logger.error("ヘルスチェックが失敗しました")
        return False
    
    def deploy(self, branch="main", skip_backup=False):
        """完全なデプロイメントプロセスを実行"""
        try:
            logger.info("=== デプロイメント開始 ===")
            
            # バックアップの作成
            if not skip_backup:
                self.backup_database()
                self.backup_application()
            
            # コードの更新
            self.update_code(branch)
            
            # 依存関係の更新
            self.update_dependencies()
            
            # データベースマイグレーション
            self.run_database_migrations()
            
            # データベース最適化
            self.optimize_database()
            
            # アプリケーション再起動
            self.restart_application()
            
            # ヘルスチェック
            if self.health_check():
                logger.info("=== デプロイメント成功 ===")
                return True
            else:
                logger.error("=== デプロイメント失敗（ヘルスチェック） ===")
                return False
                
        except Exception as e:
            logger.error(f"=== デプロイメント失敗: {e} ===")
            return False
    
    def rollback(self, backup_timestamp):
        """ロールバックを実行"""
        logger.info(f"ロールバックを開始: {backup_timestamp}")
        
        try:
            # アプリケーションファイルの復元
            backup_file = self.backup_dir / f"app_backup_before_deploy_{backup_timestamp}.tar.gz"
            if backup_file.exists():
                self.run_command(f"tar -xzf {backup_file} -C {self.app_dir.parent}")
                logger.info("アプリケーションファイル復元完了")
            
            # データベースの復元
            db_backup_file = self.backup_dir / f"db_backup_before_deploy_{backup_timestamp}.sql"
            if db_backup_file.exists() and os.environ.get('DATABASE_URL', '').startswith('postgresql'):
                db_url = os.environ.get('DATABASE_URL')
                self.run_command(f"psql '{db_url}' < {db_backup_file}")
                logger.info("データベース復元完了")
            
            # アプリケーション再起動
            self.restart_application()
            
            # ヘルスチェック
            if self.health_check():
                logger.info("=== ロールバック成功 ===")
                return True
            else:
                logger.error("=== ロールバック失敗 ===")
                return False
                
        except Exception as e:
            logger.error(f"=== ロールバック失敗: {e} ===")
            return False

def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python deploy.py deploy [branch]       - デプロイメント実行")
        print("  python deploy.py rollback [timestamp]  - ロールバック実行")
        print("  python deploy.py health                 - ヘルスチェックのみ")
        sys.exit(1)
    
    deployer = DeploymentManager()
    command = sys.argv[1]
    
    if command == "deploy":
        branch = sys.argv[2] if len(sys.argv) > 2 else "main"
        success = deployer.deploy(branch)
        sys.exit(0 if success else 1)
        
    elif command == "rollback":
        if len(sys.argv) < 3:
            print("タイムスタンプを指定してください")
            sys.exit(1)
        timestamp = sys.argv[2]
        success = deployer.rollback(timestamp)
        sys.exit(0 if success else 1)
        
    elif command == "health":
        success = deployer.health_check()
        sys.exit(0 if success else 1)
        
    else:
        print(f"不明なコマンド: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()