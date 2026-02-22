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
    
    # Diagnosis State
    definite_diagnosis: Optional[str] # Raw text diagnosis
    diagnostic_question: Optional[str]
    is_critical: Optional[bool]
    diagnosis_confidence: Optional[float]
    explanation: Optional[str] # Output of the explain node
    
    # Diagnosis Subgraph State
    patient_info: Optional[dict] # Stores the extracted PatientInfo
    missing_keys: Optional[List[str]]
    diagnosis_complete: Optional[bool]

    # Diagnosis State (Original - kept for compatibility if needed, using 'diagnosis' as final result)
    duration: Optional[str]
    symptoms: Optional[str]
    allergies: Optional[str]
    diagnosis: Optional[str]
    
    # Shopping State
    shopping_interested: Optional[bool]
    shopping_intent: Optional[bool]  # From ThinkingNode: True if user asks for products
    search_results: Optional[List[dict]]  # Raw Tavily search results

    # Thinking / Planning State
    todo: Optional[List[str]]
    thinking_process: Optional[str]
    next_step: Optional[Literal['general_chat', 'diagnosis', 'shopping_search', 'explain']]
    language: Optional[str] # Detected language of the user

# --- Structured Outputs (Pydantic V1 for LangChain compatibility) ---
from pydantic.v1 import BaseModel as BaseModelV1, Field as FieldV1

class ThinkingResult(BaseModelV1):
    analysis: str = FieldV1(description="Extremely brief medical analysis.")
    todo: List[str] = FieldV1(description="Plan of action. Must be a list of 2-5 concise bullet points.")
    next_step: Literal['general_chat', 'diagnosis', 'shopping_search']
    language: str = FieldV1(description="Detected language of the user (e.g., 'English', 'Thai', 'Chinese', 'Spanish').")

class DiagnosisResult(BaseModelV1):
    reasoning: str = FieldV1(description="Brief analysis of current symptoms and history. This is internal clinical thought (e.g., 'User mentioned dark circles, must rule out Allergic Shiners before assuming sleep deprivation.')")
    differential_diagnosis: List[str] = FieldV1(description="List of possible conditions (top 3).")
    next_step: Literal['ask_question', 'explain'] = FieldV1(description="Decision: Ask more info OR give diagnosis.")
    question: Optional[str] = FieldV1(None, description="If next_step is ask_question, provide ONE clear question.")
    final_diagnosis: Optional[str] = FieldV1(None, description="If next_step is explain, provide the diagnosis name.")
    is_critical: bool = FieldV1(False, description="True if immediate medical attention is needed.")
    confidence: float = FieldV1(description="Confidence score 0.0-1.0")

class QuestionResult(BaseModelV1):
    question: str = FieldV1(description="A single, concise (max 1-2 sentences), and smart question to ask the user.")

class MedicalExtraction(BaseModelV1):
    body_part: Optional[str] = FieldV1(None, description="The affected body area (Face, Hair, Skin, etc).")
    duration: Optional[str] = FieldV1(None, description="Time duration.")
    symptoms: Optional[str] = FieldV1(None, description="Symptoms descriptions.")
    allergies: Optional[str] = FieldV1(None, description="History of allergies.")
    shopping_interested: Optional[bool] = FieldV1(None, description="True if user asks for products.")

# --- Diagnosis Subgraph Models ---
class PatientInfo(BaseModelV1):
    duration: str = FieldV1(default="__MISSING__", title="Duration", description="Time duration (onset) and how long it has been.")
    location_and_spread: str = FieldV1(default="__MISSING__", title="Location and Spread", description="Location of symptoms and if it spreads.")
    associated_symptoms: str = FieldV1(default="__MISSING__", title="Associated Symptoms", description="Associated symptoms like itching, pain, bleeding.")
    medical_background: str = FieldV1(default="__MISSING__", title="Medical Background", description="History of similar conditions or underlying diseases.")
    aggravating_factors: str = FieldV1(default="__MISSING__", title="Aggravating Factors", description="Factors that precipitate or aggravate the condition (e.g., dust, food, stress, specific activities).")
    diet_history: str = FieldV1(default="__MISSING__", title="Diet History", description="Recent diet changes or relevant food intake.")
    lifestyle_and_sleep: str = FieldV1(default="__MISSING__", title="Lifestyle and Sleep", description="Sleep patterns, stress, lifestyle factors.")