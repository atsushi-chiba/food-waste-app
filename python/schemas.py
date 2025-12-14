# schemas.py
from pydantic import BaseModel, field_validator
from typing import Optional

class LossRecordInput(BaseModel):
    """廃棄記録APIが受け取る入力データを定義するスキーマ"""
    # ★ 必須項目（PydanticがNOT NULLを保証）
    user_id: int 
    item_name: str
    weight_grams: float # float型を期待
    reason_text: str
    
    # 任意項目
    notes: Optional[str] = None

    @field_validator('weight_grams')
    @classmethod
    def weight_must_be_positive(cls, v: float) -> float:
        """重量がゼロまたは正の数であることを保証する"""
        if v < 0:
            raise ValueError('重量は負の値であってはなりません。')
        return v
    
    @field_validator('item_name')
    @classmethod
    def item_name_must_not_be_empty(cls, v: str) -> str:
        """品目名が空白または空文字列でないことを保証する"""
        if not v.strip():
            raise ValueError('品目名を空白にすることはできません。')
        return v
    
    @field_validator('reason_text')
    @classmethod
    def reason_text_must_be_stripped(cls, v: str) -> str:
        """廃棄理由の前後の空白を削除する"""
        # .strip() を適用した値を返すことで、以降の処理ではクリーンな文字列が使われる
        return v.strip()