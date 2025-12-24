from flask import Blueprint, render_template, current_app # current_appをインポート
import pandas as pd
import os
import numpy as np
import logging
logger = logging.getLogger(__name__) 

# 1. Blueprintを定義 (変更なし)
bp = Blueprint('knowledge_bp', __name__, url_prefix='/knowledge')

FILE_GROUP_MAP = {
    '豆知識(料理).csv': '料理',
    '豆知識(掃除).csv': '掃除',      # 例: 新規追加するファイル
    '豆知識(その他).csv': 'その他'  # 例: 新規追加するファイル
}

# 💡 CSVファイルの相対パス (staticフォルダからの相対パス)
CSV_DIR_RELATIVE_PATH = os.path.join('static', 'excel')


def load_knowledge_data():
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
                df = pd.read_csv(csv_file_path, encoding='utf-8-sig', header=None)
            except UnicodeDecodeError:
                 df = pd.read_csv(csv_file_path, encoding='shift_jis', header=None)

            
            df = df.iloc[1:].copy()
            # カラム名は、すべてのファイルでこの順番と内容であることを前提とします
            df.columns = ['category', 'title', 'content'] 

            df.replace('', np.nan, inplace=True)
            df.dropna(subset=['title', 'content'], inplace=True) 
            
            # 💡 フィルタリンググループを割り当て
            df['filter_group'] = group
            
            all_knowledge_data.append(df)
            
        except Exception as e:
            logger.exception(f"🚨 ファイル '{file_name}' の処理中にエラーが発生しました。エラー詳細: {e}")
            continue
            
    if not all_knowledge_data:
        return [], []
        
    # すべてのデータを結合
    combined_df = pd.concat(all_knowledge_data, ignore_index=True)

    # 安定した連番IDを割り当て
    combined_df.reset_index(drop=True, inplace=True)
    combined_df['id'] = combined_df.index.astype(str)
    
    # 最終的なリストとユニークなグループ名を取得
    knowledge_list = combined_df[['id', 'category', 'title', 'content', 'filter_group']].to_dict('records')
    unique_filter_groups = combined_df['filter_group'].dropna().unique().tolist()
    
    return knowledge_list, unique_filter_groups


# 2. ルートを定義 (変更なし)
@bp.route('/')
def knowledge():
    # filter_groups が 'categories' としてテンプレートに渡される
    knowledge_data, filter_groups = load_knowledge_data()
    
    return render_template('knowledge.html', 
                            knowledge_list=knowledge_data, 
                            categories=filter_groups, # ここに ['料理', '掃除', 'その他'] のリストが入る
                            active_page='knowledge')