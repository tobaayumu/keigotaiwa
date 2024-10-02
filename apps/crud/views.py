from apps.crud.forms import UserForm, ChatForm
from apps.app import db
from apps.crud.models import User, Boss, ChatHistory
from flask import Blueprint, render_template, redirect, url_for, request, session
from flask_login import login_required, current_user
import google.generativeai as genai

crud = Blueprint(
    "crud",
    __name__,
    template_folder="templates",
    static_folder="static"
)

@crud.route('/')
@login_required
def chat():
    form = ChatForm()
    chat_history = session.get('chat_history', [])
    return render_template('crud/index.html', chat_history=chat_history, form=form)

@crud.route('/chat', methods=['POST'])
@login_required
def chat_route():
    form = ChatForm()

    if 'csrf_token' not in request.form:
        return "CSRFトークンが不足しています。"

    if 'chat_history' not in session:
        session['chat_history'] = []

    user_input = request.form['user_input']

    if user_input.lower() in ["終了", "exit", "quit"]:
        session.pop('chat_history', None)
        return redirect(url_for("crud.model_chat_history"))

    # チャットの初期化と履歴設定
    chat_history = [{"role": item["role"], "parts": [{"text": item["text"]}]} for item in session['chat_history']]

    # 現在のユーザーを取得
    user = current_user

    # ユーザーのboss_idに基づいてBossを取得
    boss = Boss.query.get(user.boss_id) if user.boss_id else None

    # Bossの情報を基にプロンプトを生成
    base_prompt = (
        user.prompt 
    )

    # 話し方スタイルの設定
    if 'prompt_style' in session:
        user_prompt_style = session['prompt_style']
        prompt = f"{base_prompt} Speak in the style of: {user_prompt_style}."
    else:
        prompt = base_prompt

    # Generative Modelの初期化
    chat = genai.GenerativeModel("gemini-pro").start_chat(history=chat_history)

    # ユーザーの入力とプロンプトを組み合わせた入力を生成
    full_input = f"{prompt}\nUser: {user_input}"

    try:
        # send_messageにプロンプトとユーザー入力を送信
        response = chat.send_message(full_input)

        # responseからテキストを取得
        response_text = response.text

        # チャット履歴にユーザーの入力とモデルの返答を追加
        session['chat_history'].append({"role": "user", "text": user_input})
        session['chat_history'].append({"role": "model", "text": response_text})

        # データベースにユーザーとモデルの発言を保存
        user_chat = ChatHistory(user_id=user.id, role="user", text=user_input)
        model_chat = ChatHistory(user_id=user.id, role="model", text=response_text)
        db.session.add(user_chat)
        db.session.add(model_chat)
        db.session.commit()

        # セッションのチャット履歴を更新
        session.modified = True
        return render_template('crud/index.html', chat_history=session['chat_history'], form=form)
    except Exception as e:
        return f"応答中にエラーが発生しました: {e}"


@crud.route("/sql")
@login_required
def sql():
    db.session.query(User).all()
    return "コンソールログを確認してください"

@crud.route("/users/new", methods=["GET", "POST"])
@login_required
def create_user():
    form = UserForm()
    if form.validate_on_submit():
        user = User(            
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )
        db.session.add(user)
        db.session.commit()
        # "ログイン画面に遷移するように変更"
        return redirect(url_for("crud.users"))
    return render_template("crud/create.html", form=form)

@crud.route("/users", methods=["GET", "POST"])
@login_required
def users():
    return render_template("crud/index.html")

# プロンプトから初期メッセージを生成する関数
def generate_initial_prompt():
    # プロンプトの内容を定義
    prompt = "あなたは｛敬語を判定するロボット｝です。user側とmodelが行う対話の会話が正しい敬語を使用できているかを評価してもらいたい。尊敬語か丁寧語か謙譲語かを判定させる。"

    # チャットの初期化（履歴は空）
    chat_history = []

    # Generative Modelの初期化
    chat = genai.GenerativeModel("gemini-pro").start_chat(history=chat_history)

    try:
        # geminiモデルにプロンプトを送信し、応答を取得
        response = chat.send_message(prompt)
        
        # responseからテキストを取得
        model_response = response.text.strip()

        return model_response
    except Exception as e:
        # エラーハンドリング
        return f"エラーが発生しました: {e}"

@crud.route('/chat_history/model')
@login_required
def model_chat_history():
    # プロンプトに基づいてメッセージを毎回生成
    initial_message = generate_initial_prompt()

    # ログインしているユーザーのモデルからの発言を全て取得
    model_chats = ChatHistory.query.filter_by(user_id=current_user.id, role="model").all()

    # 取得した会話と新しい初期メッセージをテンプレートに渡す
    return render_template('crud/model_chat_history.html', model_chats=model_chats, initial_message=initial_message)
