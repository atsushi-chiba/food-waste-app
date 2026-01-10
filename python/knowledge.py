import logging
from flask import Blueprint, render_template, current_app,session # current_appをインポート
import os
import csv
# ---〇変更点---
from database import get_db
from models import arrange_suggest
# ---ここまで---
logger = logging.getLogger(__name__)

# 1. Blueprintを定義 (変更なし)
bp = Blueprint('knowledge_bp', __name__, url_prefix='/knowledge')
    

FILE_GROUP_MAP = {
    '豆知識(料理).csv': '料理',
    '豆知識(掃除).csv': '掃除',    
    '豆知識(可食部).csv': '可食部',  
    '豆知識(その他).csv': 'その他'  
}

# 💡 CSVファイルの相対パス (staticフォルダからの相対パス)
CSV_DIR_RELATIVE_PATH = os.path.join("static", "excel")  # 小文字のstaticに修正

def load_knowledge_data():
    """標準ライブラリでCSV読み込み（pandas不使用）"""
    base_dir = os.path.dirname(current_app.root_path)
    csv_base_dir = os.path.join(base_dir, CSV_DIR_RELATIVE_PATH)

    # デバッグ情報を追加
    logger.info(f"アプリルートパス: {current_app.root_path}")
    logger.info(f"ベースディレクトリ: {base_dir}")
    logger.info(f"CSVディレクトリ: {csv_base_dir}")
    
    # ディレクトリの存在確認
    if os.path.exists(csv_base_dir):
        logger.info(f"CSVディレクトリが存在します: {csv_base_dir}")
        files_in_dir = os.listdir(csv_base_dir)
        logger.info(f"ディレクトリ内のファイル: {files_in_dir}")
    else:
        logger.warning(f"CSVディレクトリが見つかりません: {csv_base_dir}")

    all_knowledge_data = []

    for file_name, group in FILE_GROUP_MAP.items():
        csv_file_path = os.path.join(csv_base_dir, file_name)

        if not os.path.exists(csv_file_path):
            logger.warning(f"CSVファイルが見つかりません: {csv_file_path}")
            continue

        logger.info(f"CSVファイルを処理中: {csv_file_path}")
        
        try:
            # 標準ライブラリのcsvモジュールを使用
            with open(csv_file_path, 'r', encoding='utf-8-sig', newline='') as file:
                csv_reader = csv.reader(file)
                row_count = 0
                for row in csv_reader:
                    if len(row) >= 2 and row[0] and row[1]:  # 空行や不完全な行をスキップ
                        knowledge_item = {
                            "id": len(all_knowledge_data) + 1,
                            "name": row[0].strip(),
                            "description": row[1].strip(),
                            "category": group
                        }
                        all_knowledge_data.append(knowledge_item)
                        row_count += 1
                        
                logger.info(f"ファイル {file_name} から {row_count} 件のデータを読み込みました")
                        
        except UnicodeDecodeError:
            # UTF-8で読めない場合はShift_JISで試行
            try:
                with open(csv_file_path, 'r', encoding='shift_jis', newline='') as file:
                    csv_reader = csv.reader(file)
                    row_count = 0
                    for row in csv_reader:
                        if len(row) >= 2 and row[0] and row[1]:
                            knowledge_item = {
                                "id": len(all_knowledge_data) + 1,
                                "name": row[0].strip(),
                                "description": row[1].strip(),
                                "category": group
                            }
                            all_knowledge_data.append(knowledge_item)
                            row_count += 1
                    logger.info(f"ファイル {file_name} から {row_count} 件のデータを読み込みました (Shift_JIS)")
            except Exception as e:
                logger.error(f"CSVファイル読み込みエラー {csv_file_path}: {e}")
                continue
        except Exception as e:
            logger.error(f"CSVファイル読み込みエラー {csv_file_path}: {e}")
            continue

    # フィルターグループを生成
    filter_groups = list(FILE_GROUP_MAP.values())
    
    logger.info(f"豆知識データ読み込み完了: {len(all_knowledge_data)}件")
    logger.info(f"フィルターグループ: {filter_groups}")
    
    return all_knowledge_data, filter_groups  # 2つの値を返す

def get_all_knowledge_data():
    """豆知識データを取得"""
    knowledge_data, _ = load_knowledge_data()  # フィルターグループは無視
    return knowledge_data


# 2. ルートを定義 (変更なし)
@bp.route('/')
def knowledge():
    # filter_groups が 'categories' としてテンプレートに渡される
    knowledge_data, filter_groups = load_knowledge_data()
    

    # ---〇変更点---
    # ログインユーザーの保存済みアレンジレシピを取得
    arrange_list = []
    if 'user_id' in session:
        db = next(get_db())
        try:
            # レシピが保存されているもの（空でないもの）を取得
            records = db.query(arrange_suggest).filter(
                arrange_suggest.user_id == session['user_id'],
                arrange_suggest.arrange_recipe != None,
                arrange_suggest.arrange_recipe != ""
            ).all()
            
            for r in records:
                arrange_list.append({
                    'item_name': r.item_name,
                    'recipe': r.arrange_recipe
                })
        except Exception as e:
            print(f"レシピ取得エラー: {e}")
        finally:
            db.close()
    # ---ここまで---

    return render_template('knowledge.html', 
                            knowledge_list=knowledge_data, 
                            categories=filter_groups, # ここに ['料理', '掃除', 'その他'] のリストが入る
                            arrange_list=arrange_list, # 変更: レシピリストをテンプレートに渡す
                            active_page='knowledge')
