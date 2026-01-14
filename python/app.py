# app.py
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
from database import init_db, get_db
from auth_service import verify_login
# schemas削除：Renderビルド問題対応
from datetime import datetime, timedelta, timezone, date
from knowledge import bp as knowledge_bp
# pydantic削除：Renderビルド問題対応
from services import (
    register_new_user,
    add_new_loss_record_direct,
    get_user_by_username,  # ログイン認証用
    calculate_weekly_points_logic,  # ポイント計算ロジック
    get_user_by_id,
    get_weekly_stats,
    get_all_loss_reasons,
    register_leftover_item,
    get_user_profile,
    get_arrange_recipe_text
    # ★ get_user_by_id など、services.pyで定義した関数は必要に応じてインポート
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- アプリケーション初期設定 ---
app = Flask(__name__, template_folder="../templates", static_folder="../static")

app.register_blueprint(knowledge_bp)

# ★ 必須: セッションを使うためのSECRET_KEYを設定する ★
# 本番環境では環境変数から読み込む必要があります
app.secret_key = "a_secure_and_complex_secret_key"
init_db()

# --- 画面ルーティング ---
# ★ ログイン必須のチェック（セッション確認）を追加 ★

def login_required(func):
    """ログインしているかチェックするデコレータ"""

    def wrapper(*args, **kwargs):

        # --- ★デバッグ用に追加 (ここから)★ ---
        logger.debug(f"--- デコレータ実行 ({func.__name__}) ---")
        logger.debug(f"現在のセッション: {session}")
        # --- ★デバッグ用に追加 (ここまで)★ ---

        if "user_id" not in session:
            logger.debug(
                "セッションに user_id が見つからないため /login へリダイレクトします"
            )  # ★デバッグ用
            return redirect(url_for("login"))

        logger.debug("セッションOK。ページを表示します。")  # ★デバッグ用
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


@app.route("/")
def index():
    # ログインしていない場合は、ログインページを表示
    if "user_id" not in session:
        return render_template("login.html")
    
    # ログイン済みの場合は入力ページにリダイレクト
    return redirect(url_for("input"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    GET: アカウント作成ページを表示
    POST: アカウント作成処理を実行
    """

    # --- POSTリクエスト（フォームが送信された）の場合 ---
    if request.method == "POST":
        # 1. フォームからデータを取得
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")

        # 2. バリデーション（入力チェック）
        if not all([email, username, password, password_confirm]):
            return render_template(
                "register.html", error="すべての項目を入力してください。"
            )

        if len(password) < 8:
            return render_template("register.html", error="パスワードは8文字以上で入力してください。")

        if password != password_confirm:
            return render_template("register.html", error="パスワードが一致しません。")

        # 3. データベース処理
        db = next(get_db())
        try:
            # 4. Services層を呼び出して登録
            register_new_user(db, username, email, password)

            # 5. 成功したらログインページにリダイレクト
            # (注: ここで自動的にログインさせることも可能ですが、
            #  まずは登録後に手動でログインする流れにします)
            return redirect(url_for("login"))

        except ValueError as e:
            # 6. サービス層からのエラー（重複など）をキャッチ
            db.rollback()
            return render_template("register.html", error=str(e))
        except Exception as e:
            # その他のDBエラーなど
            logger.exception(f"致命的なエラーが発生しました: {e}")
            db.rollback()
            return render_template(
                "register.html", error=f"エラーが発生しました: {str(e)}"
            )
        finally:
            db.close()

    # --- GETリクエスト（ページにアクセスした）の場合 ---
    return render_template("register.html")


@app.route("/input", methods=["GET", "POST"])
@login_required
def input():
    today = date.today()
    user_id = session.get("user_id")
    db = next(get_db())
    
    success_message = None
    error_message = None

    if request.method == "POST":
        try:
            form_data = request.form.to_dict()
            
            # --- フードロス記録の処理 ---
            food_loss_item_name = form_data.get("item_name")
            weight_grams = form_data.get("weight_grams")
            reason_text = form_data.get("reason_text")

            # 必須項目のバリデーション
            missing_fields = []
            if not food_loss_item_name or food_loss_item_name.strip() == "":
                missing_fields.append("料理名 / 廣棄品目名")
            if not weight_grams or weight_grams.strip() == "":
                missing_fields.append("廣棄量")
            elif not weight_grams.isdigit() or int(weight_grams) <= 0:
                missing_fields.append("廣棄量（正の数値を入力してください）")
            if not reason_text:
                missing_fields.append("廣棄理由")

            if missing_fields:
                error_message = f"以下の項目を入力してください： {', '.join(missing_fields)}"
                is_food_loss_input = False
            else:
                is_food_loss_input = True

            if is_food_loss_input:
                loss_data = {
                    "user_id": user_id,
                    "item_name": food_loss_item_name,
                    "weight_grams": weight_grams,
                    "reason_text": reason_text,
                }
                validated_data = loss_data  # スキーマ削除対応
                add_new_loss_record_direct(db, validated_data)
                
                # --- 自動ポイント計算を実行 ---
                try:
                    logger.info(f"ユーザーID {user_id} の自動ポイント計算を実行中...")
                    point_result = calculate_weekly_points_logic(db, user_id)
                    points_awarded = point_result.get("points_added", 0)
                    
                    # 詳細ログ出力（改良版ベースライン計算対応）
                    details = point_result.get("calculation_details", {})
                    logger.info(
                        f"USER {details.get('user_id', user_id)}: "
                        f"Last week: {details.get('last_week_grams', 0)}g, "
                        f"This week: {details.get('this_week_grams', 0)}g, "
                        f"Baseline: {details.get('baseline_grams', 0):.1f}g "
                        f"({details.get('baseline_weeks_count', 0)}週のデータ), "
                        f"Last week rate: {point_result.get('rate_last_week', 0):.1f}%, "
                        f"Baseline rate: {point_result.get('rate_baseline', 0):.1f}%, "
                        f"Final rate: {point_result.get('final_reduction_rate', 0):.1f}% "
                        f"({details.get('comparison_method', 'unknown')})"
                    )
                    
                    if points_awarded > 0:
                        onboarding = " (初回ボーナス)" if point_result.get("onboarding_applied", False) else ""
                        success_message = f"フードロスを記録しました！ {points_awarded}ポイントを獲得しました{onboarding}！"
                        logger.info(f"ユーザーID {user_id} に {points_awarded}ポイントを付与しました{onboarding}")
                    else:
                        # 重複実行や条件未満の場合
                        if point_result.get("message") == "already_awarded":
                            success_message = "フードロスを記録しました！（今週のポイントは付与済みです）"
                            logger.info(f"ユーザーID {user_id} は今週既にポイント付与済みです")
                        else:
                            success_message = "フードロスを記録しました！"
                            logger.info(f"ユーザーID {user_id} はポイント付与条件を満たしていません: {point_result.get('message', '不明')}")
                except Exception as point_error:
                    # ポイント計算でエラーが発生してもレコード追加は成功として扱う
                    logger.error(f"ポイント計算エラー: {point_error}")
                    logger.error(f"ポイント計算エラー詳細: {type(point_error).__name__}: {str(point_error)}")
                    import traceback
                    logger.error(f"スタックトレース: {traceback.format_exc()}")
                    success_message = "フードロスを記録しました！"

            # --- 余りもの記録の処理 ---
            leftover_name = form_data.get("leftover_name")
            if leftover_name:
                try:
                    # 余りものをデータベースに登録し、アレンジレシピを生成
                    arrange_id = register_leftover_item(db, user_id, leftover_name)
                    logger.info(f"ユーザーID: {user_id} がアレンジレシピID: {arrange_id} を登録しました")
                    
                    if success_message:
                        success_message += " 余りものを記録し、アレンジレシピを生成しました！"
                    else:
                        success_message = "余りものを記録し、アレンジレシピを生成しました！"
                except Exception as e:
                    logger.error(f"余りもの登録エラー: {e}")
                    if success_message:
                        success_message += " 余りものの記録中にエラーが発生しました。"
                    else:
                        error_message = "余りものの記録中にエラーが発生しました。"

            # --- 両方未入力のチェック ---
            if not is_food_loss_input and not leftover_name:
                error_message = "少なくともどちらか一方のフォームを入力してください。"

        except ValueError as e:
            error_message = "入力内容に誤りがあります。"
            logger.error(f"バリデーションエラー: {str(e)}")
        except Exception as e:
            db.rollback()
            error_message = f"サーバーエラーが発生しました: {str(e)}"
            logger.exception("サーバーエラー")
        finally:
            db.close()

    # --- GETリクエストまたはPOST処理後のレンダリング ---
    # URLクエリのメッセージを優先
    final_success_message = request.args.get("success_message") or success_message
    final_error_message = request.args.get("error_message") or error_message

    # POSTリクエストで成功した場合はモーダルを表示
    show_modal = success_message is not None

    return render_template(
        "input.html", 
        today=today, 
        active_page="input", 
        success_message=final_success_message,
        error_message=final_error_message,
        show_modal=show_modal
    )



@app.route("/log")
@login_required
def log():
    # --- 基準日の取得 ---
    # URLのクエリパラメータから日付を取得しようと試みる
    date_str = request.args.get("date")

    target_date = None
    if date_str:
        try:
            # 文字列をdateオブジェクトに変換
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            # フォーマットが不正な場合は今日の日付を使用
            target_date = date.today()
    else:
        # パラメータがなければ今日の日付を使用
        target_date = date.today()

    # --- 週の計算 ---
    # 基準日をもとに、その週の日曜日を計算
    start_of_week = target_date - timedelta(days=(target_date.weekday() + 1) % 7)
    end_of_week = start_of_week + timedelta(days=6)

    # --- 1週間分の日付リストを作成 ---
    week_dates = []
    jp_weekdays = ["日", "月", "火", "水", "木", "金", "土"]
    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        week_dates.append(
            {
                "date": current_day,
                "day_num": current_day.day,
                "weekday_jp": jp_weekdays[(current_day.weekday() + 1) % 7],
            }
        )

    # --- 前週と次週の日付を計算 ---
    # 表示している週の日曜から7日前と7日後を計算
    prev_week_date = start_of_week - timedelta(days=7)
    next_week_date = start_of_week + timedelta(days=7)

    # --- 表示用の日付範囲を作成 ---
    week_range_str = f"{start_of_week.month}月{start_of_week.day}日 〜 {end_of_week.month}月{end_of_week.day}日"

    # HTMLテンプレートにデータを渡してレンダリング
    return render_template(
        "log.html",
        today=date.today(),  # 「今日」をハイライトするために別途渡す
        week_dates=week_dates,
        week_range=week_range_str,
        prev_week=prev_week_date.strftime("%Y-%m-%d"),
        next_week=next_week_date.strftime("%Y-%m-%d"),
        active_page="log",
    )


@app.route("/points")
@login_required
def points():
    user_id = session["user_id"]
    db = next(get_db())

    try:
        # services.py の get_user_profile を呼び出す想定
        profile = get_user_profile(db, user_id)
        total_points = profile["total_points"] if profile else 0

        return render_template(
            "points.html",
            total_points=total_points,  # ★ テンプレートに渡す ★
            active_page="points",
        )
    except Exception as e:
        logger.exception(f"ポイント取得エラー: {e}")
        return render_template(
            "points.html",
            total_points=0,
            error_message="ポイント情報の取得に失敗しました。",
            active_page="points",
        )
    finally:
        db.close()


@app.route("/account")
@login_required
def account():
    # 1. セッションからユーザーIDを取得
    user_id = session["user_id"]

    db = next(get_db())
    try:
        # 2. データベースからユーザー情報を取得
        # (services.py の get_user_by_id 関数を使用)
        current_user = get_user_by_id(db, user_id)

        if not current_user:
            # 万が一、DBからユーザーが削除されていた場合
            # 強制的にログアウトさせ、ログインページに戻す
            session.pop("user_id", None)
            return redirect(url_for("login"))

        # 3. 取得したユーザー情報を 'user' という名前でHTMLに渡す
        return render_template(
            "account.html",
            active_page="account",
            user=current_user,  # ★ ユーザーオブジェクトを渡す
        )
    except Exception:
        # DBエラーなどが発生した場合
        return render_template(
            "account.html",
            active_page="account",
            error="アカウント情報の取得に失敗しました。",
        )
    finally:
        db.close()


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        db = next(get_db())
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            user = get_user_by_username(db, username) 
            if user and verify_login(username, password, user.password):
                session['user_id'] = user.id
                
                # シンプルなログイン - input.htmlへ直接リダイレクト
                today = date.today()
                return render_template(
                    'input.html',
                    today=today,
                    active_page='input'
                )
                
            else:
                return render_template('login.html', error="ユーザー名またはパスワードが正しくありません。")

        except Exception as e:
            logger.exception(f"--- エラー発生: {str(e)} ---")
            return render_template(
                "login.html", error=f"エラーが発生しました: {str(e)}"
            )
        finally:
            db.close()

    # GETリクエスト（ページにアクセスした）の場合
    # @login_required からのリダイレクトもここに来る
    logger.debug("--- GETリクエスト /login ページ表示 ---")
    return render_template("login.html")


@app.route("/logout")
def logout():
    """サインアウト処理"""
    # セッションを完全にクリア
    session.clear()
    return redirect(url_for('index'))


# --- ここまで画面ルーティング ---


# --- API: ユーザー登録 ---
@app.route("/api/register_user", methods=["POST"])
def register_user_api():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not all([username, email, password]):
        return jsonify({"message": "すべての情報が必要です。"}), 400
    
    if len(password) < 8:
        return jsonify({"message": "パスワードは8文字以上で入力してください。"}), 400

    db = next(get_db())
    try:
        # ★ Services層を呼び出し、DB操作を任せる ★
        user_id = register_new_user(db, username, email, password)

        return jsonify({"message": "登録完了！", "user_id": user_id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"message": f"登録エラー: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/add_loss_record", methods=["POST"])
def add_loss_record_api():
    # ユーザーIDはセッションから取得する (最優先)
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"message": "認証が必要です。再ログインしてください。"}), 401

    data = request.get_json()
    data["user_id"] = user_id  # Services層に渡すデータに user_id を追加

    # 必須項目チェック (手動チェックは削除)

    db = next(get_db())
    try:
        # ★ 1. データの基本検証 ★
        validated_data = data  # スキーマ削除対応

        # 2. Services層へ処理を渡す
        record_id = add_new_loss_record_direct(db, validated_data)
        # NOTE: validated_data.model_dump() でPydanticオブジェクトをPython辞書に変換して渡す

        return jsonify({"message": "記録完了！", "record_id": record_id}), 201

    except ValueError as e:
        # ★ バリデーションエラーを捕捉し、422を返す ★
        return (
            jsonify({"message": "入力データが無効です", "details": str(e)}),
            422,
        )  # 422 Unprocessable Entity
    except Exception as e:
        db.rollback()
        return jsonify({"message": f"記録エラー: {str(e)}"}), 500
    finally:
        db.close()


# --- API: 週次ポイント計算 ---
@app.route("/api/calculate_weekly_points", methods=["POST"])
def calculate_weekly_points_api():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"message": "認証が必要です。"}), 401

    db = next(get_db())
    try:
        # ★ Services層を呼び出し、ロジックを実行させる ★
        result = calculate_weekly_points_logic(db, user_id)

        return jsonify({"message": "週次ポイントを計算・付与しました。", **result}), 200

    except Exception as e:
        db.rollback()
        return (
            jsonify({"message": f"ポイント計算中にエラーが発生しました: {str(e)}"}),
            500,
        )
    finally:
        db.close()


@app.route("/api/loss_reasons", methods=["GET"])
def get_loss_reasons_api():
    """フロントエンドのドロップダウンリスト用の廃棄理由を返すAPI"""
    db = next(get_db())
    try:
        # Services層の関数を呼び出す
        reasons_list = get_all_loss_reasons(db)

        return jsonify({"reasons": reasons_list}), 200
    except Exception as e:
        return (
            jsonify({"message": f"理由の取得中にエラーが発生しました: {str(e)}"}),
            500,
        )
    finally:
        db.close()


@app.route("/api/user/me", methods=["GET"])
def get_user_profile_api():
    """ログイン中のユーザーのプロフィール情報を返すAPI"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"message": "認証が必要です。"}), 401

    db = next(get_db())
    try:
        profile_data = get_user_profile(db, user_id)

        if not profile_data:
            return jsonify({"message": "ユーザーが見つかりません。"}), 404

        return jsonify(profile_data), 200
    except Exception as e:
        return (
            jsonify(
                {"message": f"プロフィールの取得中にエラーが発生しました: {str(e)}"}
            ),
            500,
        )
    finally:
        db.close()


@app.route("/api/redeem", methods=["POST"])
def redeem_api():
    """ポイント交換処理: 要認証。リクエスト JSON に item_name, cost を期待する"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"message": "認証が必要です。再ログインしてください。"}), 401

    data = request.get_json() or {}
    item_name = data.get("item_name")
    cost = data.get("cost")

    if not item_name or cost is None:
        return jsonify({"message": "item_name と cost が必要です。"}), 400

    try:
        cost = int(cost)
        if cost <= 0:
            return jsonify({"message": "無効な cost 値です。"}), 400
    except Exception:
        return jsonify({"message": "cost は整数でなければなりません。"}), 400

    db = next(get_db())
    try:
        user = get_user_by_id(db, user_id)
        if not user:
            return jsonify({"message": "ユーザーが見つかりません。"}), 404

        if user.total_points < cost:
            return (
                jsonify(
                    {
                        "message": "ポイントが不足しています。",
                        "current_points": user.total_points,
                    }
                ),
                403,
            )

        # ポイントを減算して確定
        user.total_points -= cost
        db.commit()

        return (
            jsonify(
                {
                    "message": f"{item_name} を交換しました。",
                    "remaining_points": user.total_points,
                }
            ),
            200,
        )

    except Exception as e:
        db.rollback()
        return jsonify({"message": f"交換処理中にエラーが発生しました: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/weekly_stats", methods=["GET"])
def get_weekly_stats_api():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"message": "認証が必要です。"}), 401

    # URLクエリパラメータから基準日を取得
    date_str = request.args.get("date")
    # main-test の実装を優先: シンプルに date を使う
    target_date = date.today()
    if date_str:
        try:
            # log.htmlが渡す 'YYYY-MM-DD' 形式を解析
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass  # 不正な場合は今日の日付を使用

    db = next(get_db())
    try:
        # Services層を呼び出し、週次データを取得
        stats_data = get_weekly_stats(db, user_id, target_date)

        return jsonify(stats_data), 200

    except Exception as e:
        return (
            jsonify({"message": f"統計データの取得中にエラーが発生しました: {str(e)}"}),
            500,
        )
    finally:
        db.close()


# ---〇変更点---
# 1. 残った食品を入力するフォームのデータを受け取るAPI
@app.route("/api/register_leftover", methods=["POST"])
def register_leftover_api():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "認証が必要です。"}), 401
    
    data = request.get_json()
    data["user_id"] = user_id
    
    db = next(get_db())
    try:
        validated_data = data  # スキーマ削除対応
        #下一行はデバッグ用のprint文　消していい
        print(f"登録データ: {validated_data}")
        # サービス層を通してDBに保存
        record_id = register_leftover_item(db, validated_data["user_id"], validated_data["item_name"])
        
        return jsonify({"message": "食材を登録しました", "id": record_id}), 201
    except ValueError as e:
        return jsonify({"message": "入力データが無効です", "details": str(e)}), 422
    except Exception as e:
        db.rollback()
        return jsonify({"message": f"登録エラー: {str(e)}"}), 500
    finally:
        db.close()

# 2. アレンジレシピのテキストデータを返すAPI
@app.route("/api/get_arrange_recipe", methods=["POST"])
def get_arrange_recipe_api():
    # 本来は登録したID等を受け取るか、食材名を直接受け取る
    # ここでは食材名(item_name)を受け取ってレシピを返す想定
    data = request.get_json()
    item_name = data.get("item_name")
    
    if not item_name:
        return jsonify({"message": "食材名が必要です"}), 400
        
    try:
        recipe_text = get_arrange_recipe_text(item_name)
        return jsonify({"recipe": recipe_text}), 200
    except Exception as e:
        return jsonify({"message": f"レシピ生成エラー: {str(e)}"}), 500
# ---ここまで---

# --- 統計レポート機能（管理者専用） ---
# 注意: これらの機能はWebからアクセス可能ですが、
# 一般ユーザー向けのUIには表示されません


# --- サーバー実行 ---
if __name__ == "__main__":
    # Flaskサーバーを起動
    app.run(debug=True)
