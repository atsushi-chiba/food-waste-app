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
CSV_DIR_RELATIVE_PATH = os.path.join("static", "excel")

def load_knowledge_data():
    """一時的に無効化：pandas依存関係問題対応"""
    return []

def get_all_knowledge_data():
    """一時的に無効化：pandas依存関係問題対応"""  
    return []
    base_dir = os.path.dirname(current_app.root_path)
    csv_base_dir = os.path.join(base_dir, CSV_DIR_RELATIVE_PATH)

    all_knowledge_data = []

    for file_name, group in FILE_GROUP_MAP.items():
        csv_file_path = os.path.join(csv_base_dir, file_name)

        if not os.path.exists(csv_file_path):
            logger.warning(f"⚠️ 警告: ファイルが見つかりません: {csv_file_path}")
            continue

        try:
            # CSV読み込み部分
            try:
                df = pd.read_csv(csv_file_path, encoding="utf-8-sig", header=None)
            except UnicodeDecodeError:
                df = pd.read_csv(csv_file_path, encoding="shift_jis", header=None)

            df = df.iloc[1:].copy()
            
            # テンプレートでの category の有無チェックを有効にするため、まず空文字列をNaNに変換
            df.replace('', np.nan, inplace=True) 
            
            # カラム名は、すべてのファイルでこの順番と内容であることを前提とします
            
            if df.shape[1] == 2:
                # 2列の場合 (例: title, content のみ)
                df.columns = ['title', 'content'] 
                # テンプレートで category が False と判定されるように None を設定
                df['category'] = None 
            elif df.shape[1] == 3:
                # 3列の場合 (例: category, title, content の全てがCSVに含まれている)
                df.columns = ['category', 'title', 'content'] 
                
                # 【修正点】fillna(None)の代わりにreplace(np.nan, None)を使用して、
                # NaNをPythonのNoneに変換する
                df['category'] = df['category'].replace(np.nan, None)
            else:
                # 2列または3列でない場合は警告を出してスキップ
                print(f"⚠️ 警告: ファイル '{file_name}' の列数が予期しない値です ({df.shape[1]} 列)。2列(title, content)または3列(category, title, content)を想定しています。")
                continue

            # title, contentがNaN（空欄）の行は削除
            df.dropna(subset=['title', 'content'], inplace=True) 
            
            # 💡 フィルタリンググループを割り当て
            df["filter_group"] = group

            all_knowledge_data.append(df)

        except Exception as e:
            logger.exception(
                f"🚨 ファイル '{file_name}' の処理中にエラーが発生しました。エラー詳細: {e}"
            )
            continue

    if not all_knowledge_data:
        return [], []

    # すべてのデータを結合
    combined_df = pd.concat(all_knowledge_data, ignore_index=True)

    # 安定した連番IDを割り当て
    combined_df.reset_index(drop=True, inplace=True)
    combined_df["id"] = combined_df.index.astype(str)

    # 最終的なリストとユニークなグループ名を取得
    # Noneを含む可能性があるため、object型にキャスト
    combined_df['category'] = combined_df['category'].astype(object) 
    knowledge_list = combined_df[['id', 'category', 'title', 'content', 'filter_group']].to_dict('records')
    unique_filter_groups = combined_df['filter_group'].dropna().unique().tolist()
    
    return knowledge_list, unique_filter_groups


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
