from typing import List, Optional, Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# --- API Models ---
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = [] 
    context: Optional[str] = "No specific skin condition detected yet."
    image_url: Optional[str] = None
    thread_id: Optional[str] = None

# --- Domain/Graph State Models ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    context: str
    image_url: Optional[str]
    
    # Diagnostic State
    duration: Optional[str]
    symptoms: Optional[str]  # itching, pain
    allergies: Optional[str]
    diagnosis: Optional[str]
    
    # Shopping State
    shopping_interested: Optional[bool]

    # Thinking / Planning State
    todo: Optional[List[str]]
    next_step: Optional[Literal['general_chat', 'interview', 'diagnosis', 'shopping_search']]