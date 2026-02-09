from typing import List, Optional, Annotated
from typing_extensions import TypedDict
from pydantic import BaseModel
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# --- API Models ---
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = [] # [{'role': 'user', 'content': '...'}, ...]
    context: Optional[str] = "No specific skin condition detected yet."
    image_url: Optional[str] = None

# --- Domain/Graph State Models ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    context: str
    image_url: Optional[str]
