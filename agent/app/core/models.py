from typing import List, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel
from langchain_core.messages import BaseMessage

# --- API Models ---
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = [] # [{'role': 'user', 'content': '...'}, ...]
    context: Optional[str] = "No specific skin condition detected yet."
    image: Optional[str] = None  # Base64 data URL of segmentation image

# --- Domain/Graph State Models ---
class AgentState(TypedDict):
    messages: List[BaseMessage]
    context: str

