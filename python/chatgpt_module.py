import openai
import os
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """
あなたは「食品ロス削減」に特化したアレンジ提案AIです。

【役割】
・ユーザーが入力した文章を読み取り、
・余っている食品や状況を推測し、
・食品ロスを減らすための調理・再利用案を1つ提案してください。

【制約】
・前置きや挨拶は不要
・簡潔で実用的に
・家庭で再現できる内容のみ
・出力は日本語

【出力形式】
■ 提案内容
■ 材料（推測でOK）
■ 手順（3〜5ステップ）
"""

def generate_recipe_from_text(user_text: str) -> str:
    if not user_text or not user_text.strip():
        raise ValueError("入力テキストが空です")

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        max_tokens=400,
        temperature=0.6
    )

    return response.choices[0].message["content"].strip()
