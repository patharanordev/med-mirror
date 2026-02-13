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
    run_id: Optional[str] = None

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

# --- Structured Outputs (Pydantic V1 for LangChain compatibility) ---
from pydantic.v1 import BaseModel as BaseModelV1, Field as FieldV1

class ThinkingResult(BaseModelV1):
    analysis: str = FieldV1(description="Extremely brief medical analysis.")
    todo: List[str] = FieldV1(description="Plan of action. Must be a list of 2-5 concise bullet points.")
    next_step: Literal['general_chat', 'interview', 'diagnosis', 'shopping_search']

class QuestionResult(BaseModelV1):
    question: str = FieldV1(description="A single, concise (max 1-2 sentences), and smart question to ask the user.")

class MedicalExtraction(BaseModelV1):
    body_part: Optional[str] = FieldV1(None, description="The affected body area (Face, Hair, Skin, etc).")
    duration: Optional[str] = FieldV1(None, description="Time duration.")
    symptoms: Optional[str] = FieldV1(None, description="Symptoms descriptions.")
    allergies: Optional[str] = FieldV1(None, description="History of allergies.")
    shopping_interested: Optional[bool] = FieldV1(None, description="True if user asks for products.")