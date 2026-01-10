#!/usr/bin/env python3
"""
本番環境用データベース移行スクリプト
"""

import os
import shutil
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from database import init_db, get_db_connection
from models import Base, User, Product
import click

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """データベース移行管理ツール"""
    pass


@cli.command()
def init_production_db():
    """本番環境でのデータベース初期化"""
    try:
        logger.info("本番データベースの初期化を開始...")
        
        # データベース初期化
        init_db()
        logger.info("✓ データベーステーブルを作成しました")
        
        # 基本的な管理ユーザーを作成（必要に応じて）
        # create_admin_user()
        
        logger.info("✓ 本番データベースの初期化が完了しました")
        
    except Exception as e:
        logger.error(f"データベース初期化でエラーが発生しました: {e}")
        raise


@cli.command()
@click.argument('source_db_path')
def migrate_from_dev(source_db_path):
    """開発環境のデータベースから本番環境にデータを移行"""
    try:
        if not os.path.exists(source_db_path):
            raise FileNotFoundError(f"ソースデータベースが見つかりません: {source_db_path}")
        
        logger.info(f"開発データベース {source_db_path} からデータを移行中...")
        
        # バックアップ作成
        backup_path = f"backups/migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        os.makedirs('backups', exist_ok=True)
        shutil.copy2(source_db_path, backup_path)
        logger.info(f"✓ バックアップを作成しました: {backup_path}")
        
        # データ移行の実装
        source_engine = create_engine(f'sqlite:///{source_db_path}')
        
        with get_db_connection() as conn:
            # ユーザーデータの移行
            with source_engine.connect() as source_conn:
                users_data = source_conn.execute(text("SELECT * FROM users")).fetchall()
                
                for user_row in users_data:
                    # 本番環境での重複チェックとデータ挿入
                    existing_user = conn.execute(
                        text("SELECT id FROM users WHERE username = :username"),
                        {"username": user_row.username}
                    ).fetchone()
                    
                    if not existing_user:
                        conn.execute(text("""
                            INSERT INTO users (username, password_hash, current_points, total_points, 
                                             baseline_calculation_date, baseline_points, created_at)
                            VALUES (:username, :password_hash, :current_points, :total_points, 
                                   :baseline_calculation_date, :baseline_points, :created_at)
                        """), {
                            "username": user_row.username,
                            "password_hash": user_row.password_hash,
                            "current_points": user_row.current_points,
                            "total_points": user_row.total_points,
                            "baseline_calculation_date": user_row.baseline_calculation_date,
                            "baseline_points": user_row.baseline_points,
                            "created_at": user_row.created_at
                        })
                        logger.info(f"✓ ユーザー {user_row.username} を移行しました")
                
                # 商品データの移行
                products_data = source_conn.execute(text("SELECT * FROM products")).fetchall()
                
                for product_row in products_data:
                    existing_product = conn.execute(
                        text("SELECT id FROM products WHERE user_id = :user_id AND name = :name AND created_date = :created_date"),
                        {"user_id": product_row.user_id, "name": product_row.name, "created_date": product_row.created_date}
                    ).fetchone()
                    
                    if not existing_product:
                        conn.execute(text("""
                            INSERT INTO products (user_id, name, quantity, unit, expiration_date, 
                                                created_date, food_loss_points, baseline_reduction_points)
                            VALUES (:user_id, :name, :quantity, :unit, :expiration_date,
                                   :created_date, :food_loss_points, :baseline_reduction_points)
                        """), {
                            "user_id": product_row.user_id,
                            "name": product_row.name,
                            "quantity": product_row.quantity,
                            "unit": product_row.unit,
                            "expiration_date": product_row.expiration_date,
                            "created_date": product_row.created_date,
                            "food_loss_points": product_row.food_loss_points,
                            "baseline_reduction_points": product_row.baseline_reduction_points
                        })
                
                conn.commit()
                logger.info("✓ データ移行が完了しました")
        
    except Exception as e:
        logger.error(f"データ移行でエラーが発生しました: {e}")
        raise


@cli.command()
def backup_db():
    """現在のデータベースのバックアップを作成"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"backups/manual_backup_{timestamp}.db"
        
        os.makedirs('backups', exist_ok=True)
        
        # 現在のデータベースファイルをバックアップ
        db_path = os.getenv('DATABASE_URL', 'sqlite:///db/food_loss.db').replace('sqlite:///', '')
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            logger.info(f"✓ バックアップを作成しました: {backup_path}")
        else:
            logger.warning("データベースファイルが見つかりませんでした")
            
    except Exception as e:
        logger.error(f"バックアップ作成でエラーが発生しました: {e}")
        raise


@cli.command()
def verify_db():
    """データベースの整合性を確認"""
    try:
        logger.info("データベースの整合性確認を開始...")
        
        with get_db_connection() as conn:
            # ユーザー数
            user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            logger.info(f"ユーザー数: {user_count}")
            
            # 商品数
            product_count = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
            logger.info(f"商品数: {product_count}")
            
            # 基本整合性チェック
            orphaned_products = conn.execute(text("""
                SELECT COUNT(*) FROM products p 
                LEFT JOIN users u ON p.user_id = u.id 
                WHERE u.id IS NULL
            """)).scalar()
            
            if orphaned_products > 0:
                logger.warning(f"孤立した商品レコード: {orphaned_products}件")
            else:
                logger.info("✓ データの整合性に問題ありません")
                
        logger.info("✓ データベース整合性確認が完了しました")
        
    except Exception as e:
        logger.error(f"整合性確認でエラーが発生しました: {e}")
        raise


if __name__ == '__main__':
    cli()