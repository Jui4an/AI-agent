# src/models.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional 

class Tip(BaseModel):
    gate_line: str = Field(..., description="Формат: X.Y, например 10.6")
    advice: str = Field(..., min_length=10, max_length=500, description="Текст совета (3-5 предложений)")
    dialog_summary: Optional[str] = Field(None, max_length=200)
    date: str = Field(..., description="Дата в формате YYYY-MM-DD")

    @field_validator('gate_line')
    def validate_gate_line(cls, v):
        parts = v.split('.')
        if len(parts) != 2:
            raise ValueError("gate_line must be in format X.Y")
        try:
            a, b = map(int, parts)
            if not (1 <= a <= 64) or not (1 <= b <= 12):
                raise ValueError("Invalid gate or line numbers")
        except:
            raise ValueError("gate_line must contain integers")
        return v

class ChatRequest(BaseModel):
    session_id: str
    message: str