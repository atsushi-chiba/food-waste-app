"""
データベース最適化とバックアップスクリプト
"""
import sqlite3
import os
import shutil
import datetime
from pathlib import Path

class DatabaseOptimizer:
    """データベース最適化クラス"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            # データベースファイルのパスを正しく設定
            current_dir = os.path.dirname(__file__)
            project_root = os.path.dirname(current_dir)
            self.db_path = os.path.join(project_root, "db", "food_loss.db")
        else:
            self.db_path = db_path
        
        self.backup_dir = Path(os.path.dirname(current_dir)) / "backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self):
        """データベースのバックアップを作成"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        db_name = os.path.splitext(os.path.basename(self.db_path))[0]
        backup_filename = f"{db_name}_backup_{timestamp}.db"
        backup_path = self.backup_dir / backup_filename
        
        try:
            if not os.path.exists(self.db_path):
                print(f"データベースファイルが見つかりません: {self.db_path}")
                return None
                
            shutil.copy2(self.db_path, backup_path)
            print(f"バックアップ作成成功: {backup_path}")
            return str(backup_path)
        except Exception as e:
            print(f"バックアップ作成エラー: {e}")
            return None
    
    def optimize_database(self):
        """データベースの最適化"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # VACUUMでデータベースを最適化
            print("データベースを最適化中...")
            conn.execute("VACUUM")
            
            # 統計情報を更新
            conn.execute("ANALYZE")
            
            conn.close()
            print("データベース最適化完了")
            
        except Exception as e:
            print(f"データベース最適化エラー: {e}")
    
    def add_indexes(self):
        """パフォーマンス向上のためのインデックス追加"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_food_loss_user_id ON food_loss_records(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_food_loss_record_date ON food_loss_records(record_date)",
                "CREATE INDEX IF NOT EXISTS idx_user_username ON users(username)",
                "CREATE INDEX IF NOT EXISTS idx_user_total_points ON users(total_points)",
                "CREATE INDEX IF NOT EXISTS idx_user_last_points_week ON users(last_points_awarded_week_start)"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
                print(f"インデックス作成: {index_sql.split()[-1]}")
            
            conn.commit()
            conn.close()
            print("全インデックス作成完了")
            
        except Exception as e:
            print(f"インデックス作成エラー: {e}")
    
    def get_database_stats(self):
        """データベース統計情報を取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # テーブルごとの行数
            tables = ['users', 'food_loss_records', 'loss_reasons', 'arrange_suggest']
            stats = {}
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    stats[table] = count
                except:
                    stats[table] = 0
            
            # データベースファイルサイズ
            db_size = os.path.getsize(self.db_path) / 1024 / 1024  # MB
            stats['file_size_mb'] = round(db_size, 2)
            
            conn.close()
            return stats
            
        except Exception as e:
            print(f"❌ 統計情報取得エラー: {e}")
            return {}

def run_database_maintenance():
    """データベースメンテナンスを実行"""
    print("=== データベースメンテナンス開始 ===")
    
    optimizer = DatabaseOptimizer()
    
    # バックアップ作成
    backup_path = optimizer.create_backup()
    
    if backup_path:
        # 統計情報表示
        print("\n📊 データベース統計情報:")
        stats = optimizer.get_database_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # インデックス追加
        print("\n🗂️ インデックス最適化:")
        optimizer.add_indexes()
        
        # データベース最適化
        print("\n⚡ データベース最適化:")
        optimizer.optimize_database()
        
        print("\n=== データベースメンテナンス完了 ===")
    else:
        print("❌ バックアップに失敗したため、メンテナンスを中止します")

if __name__ == "__main__":
    run_database_maintenance()