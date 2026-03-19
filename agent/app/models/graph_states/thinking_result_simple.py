from pydantic.v1 import BaseModel as BaseModelV1, Field as FieldV1
from typing import Literal

class ThinkingResultSimple(BaseModelV1):
    analysis: str = FieldV1(description="Brief analysis of intent.")
    next_step: Literal['general_chat', 'diagnosis', 'shopping_search']
    language: str = FieldV1(description="Detected language of the user (e.g., 'English', 'Thai', 'Japanese'). Default to 'English'.")
    shopping_intent: bool = FieldV1(default=False, description="True if user explicitly asks for products, medicine, cream, or treatment.")
