# app_simple.py - 学校用簡易版
from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    make_response,
    redirect,
    url_for,
    session,
)
import logging
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()
from database import init_db, get_db
from schemas import LossRecordInput, LeftoverInput
from datetime import datetime, timedelta, timezone, date
from knowledge import bp as knowledge_bp
from pydantic import ValidationError
from services import (
    register_new_user,
    add_new_loss_record_direct,
    calculate_weekly_points_logic
)
from models import User, FoodLossRecord
import hashlib

app = Flask(__name__, 
           template_folder='../templates',
           static_folder='../Static')

# 学校用シンプル設定
app.secret_key = 'simple-secret-key-for-school-project'
app.config['DEBUG'] = True  # 開発モード

# ログ設定（シンプル）
logging.basicConfig(level=logging.INFO)

# データベース初期化
init_db()

# Blueprint登録
app.register_blueprint(knowledge_bp, url_prefix='/knowledge')

@app.route('/')
def index():
    return render_template('welcome.html')

@app.route('/register')
def register_form():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return render_template('register.html', error='ユーザー名とパスワードが必要です')
    
    try:
        result = register_new_user(username, password)
        if result['success']:
            session['user_id'] = result['user_id']
            session['username'] = username
            return redirect(url_for('welcome'))
        else:
            return render_template('register.html', error=result['message'])
    except Exception as e:
        logging.error(f"Registration error: {e}")
        return render_template('register.html', error='登録に失敗しました')

@app.route('/login')
def login_form():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return render_template('login.html', error='ユーザー名とパスワードが必要です')
    
    try:
        db = get_db()
        user = db.query(User).filter(User.username == username).first()
        
        if user and user.password_hash == hashlib.sha256(password.encode()).hexdigest():
            session['user_id'] = user.id
            session['username'] = username
            return redirect(url_for('welcome'))
        else:
            return render_template('login.html', error='ユーザー名またはパスワードが間違っています')
    except Exception as e:
        logging.error(f"Login error: {e}")
        return render_template('login.html', error='ログインに失敗しました')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/welcome')
def welcome():
    if 'user_id' not in session:
        return redirect(url_for('login_form'))
    return render_template('welcome.html', username=session.get('username'))

@app.route('/input')
def input_form():
    if 'user_id' not in session:
        return redirect(url_for('login_form'))
    return render_template('input.html')

@app.route('/add_record', methods=['POST'])
def add_record():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "ログインが必要です"}), 401
    
    try:
        data = request.get_json()
        
        # バリデーション
        record_input = LossRecordInput(**data)
        
        # レコード追加
        result = add_new_loss_record_direct(
            user_id=session['user_id'],
            item_name=record_input.item_name,
            weight_grams=record_input.weight_grams,
            reason=record_input.reason
        )
        
        if result['success']:
            return jsonify({
                "success": True, 
                "message": "レコードが追加されました",
                "points_info": result.get('points_info', {})
            })
        else:
            return jsonify({"success": False, "message": result['message']})
            
    except ValidationError as e:
        return jsonify({"success": False, "message": f"入力エラー: {str(e)}"}), 400
    except Exception as e:
        logging.error(f"Add record error: {e}")
        return jsonify({"success": False, "message": "レコード追加に失敗しました"}), 500

@app.route('/log')
def view_log():
    if 'user_id' not in session:
        return redirect(url_for('login_form'))
    return render_template('log.html')

@app.route('/api/records')
def get_records():
    if 'user_id' not in session:
        return jsonify({"error": "ログインが必要です"}), 401
    
    try:
        db = get_db()
        records = db.query(FoodLossRecord).filter(
            FoodLossRecord.user_id == session['user_id']
        ).order_by(FoodLossRecord.created_at.desc()).limit(50).all()
        
        records_data = []
        for record in records:
            records_data.append({
                'id': record.id,
                'item_name': record.item_name,
                'weight_grams': record.weight_grams,
                'reason': record.reason,
                'created_at': record.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return jsonify({"records": records_data})
    except Exception as e:
        logging.error(f"Get records error: {e}")
        return jsonify({"error": "レコード取得に失敗しました"}), 500

@app.route('/points')
def points():
    if 'user_id' not in session:
        return redirect(url_for('login_form'))
    
    try:
        db = get_db()
        user = db.query(User).filter(User.id == session['user_id']).first()
        
        return render_template('points.html', 
                             current_points=user.current_points if user else 0)
    except Exception as e:
        logging.error(f"Points page error: {e}")
        return render_template('points.html', current_points=0)

@app.route('/api/stats')
def get_stats():
    if 'user_id' not in session:
        return jsonify({"error": "ログインが必要です"}), 401
    
    try:
        # 簡易版：基本統計のみ
        db = get_db()
        user = db.query(User).filter(User.id == session['user_id']).first()
        total_records = db.query(FoodLossRecord).filter(
            FoodLossRecord.user_id == session['user_id']
        ).count()
        
        stats = {
            "total_records": total_records,
            "current_points": user.current_points if user else 0,
            "total_points": user.total_points if user else 0
        }
        return jsonify(stats)
    except Exception as e:
        logging.error(f"Stats error: {e}")
        return jsonify({"error": "統計取得に失敗しました"}), 500

@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login_form'))
    
    try:
        db = get_db()
        user = db.query(User).filter(User.id == session['user_id']).first()
        
        return render_template('account.html', 
                             username=session.get('username'),
                             total_points=user.total_points if user else 0,
                             current_points=user.current_points if user else 0)
    except Exception as e:
        logging.error(f"Account page error: {e}")
        return render_template('account.html', 
                             username=session.get('username'),
                             total_points=0, current_points=0)

@app.route('/redeem', methods=['POST'])
def redeem_points():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "ログインが必要です"}), 401
    
    try:
        data = request.get_json()
        points_to_redeem = data.get('points', 0)
        
        # 簡易版：ポイント交換機能を無効化
        return jsonify({"success": False, "message": "学校版ではポイント交換は無効です"})
    except Exception as e:
        logging.error(f"Redeem error: {e}")
        return jsonify({"success": False, "message": "ポイント交換に失敗しました"}), 500

# 健康チェック用エンドポイント
@app.route('/health')
def health_check():
    return jsonify({"status": "OK", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    print("学校用アプリを起動中...")
    print("ブラウザで http://localhost:5000 にアクセスしてください")
    app.run(host='0.0.0.0', port=5000, debug=True)