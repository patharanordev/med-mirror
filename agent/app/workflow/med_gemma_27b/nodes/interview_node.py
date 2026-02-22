from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt, Command
from app.core.config import settings
from app.core.models import AgentState, MedicalExtraction, QuestionResult

class InterviewNode:
    def __init__(self, llm):
        self.llm = llm

    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- INTERVIEW NODE ---")
        
        # Check if we have a specific question from Diagnosis Node
        question = state.get("diagnostic_question")
        
        if question:
            # 1. Ask the Dynamic Question via Interrupt
            user_answer = interrupt(question)
            
            # Handle resume value from routes.py (which sends a dict)
            if isinstance(user_answer, dict) and "interrupt_response" in user_answer:
                user_answer = user_answer["interrupt_response"]
            
            # 2. Return the answer to the state
            return {
                "messages": [
                    AIMessage(content=question),
                    HumanMessage(content=user_answer)
                ],
                # clear the question so we don't get stuck in a loop if the next node doesn't set it?
                # Actually DiagnosisNode will set a new one or clear it.
                "diagnostic_question": None 
            }
        
        # Fallback / Default Interview Logic (e.g. initial gathering if not coming from diagnosis)
        # For now, if no specific question, we might just pass or do standard interview.
        # Let's keep a simple fallback or just return END if we shouldn't be here.
        
        # If we are here without a diagnostic_question, maybe we are in the initial interview phase?
        # The original code was hardcoded for "duration". Let's preserve a basic behavior or just pass.
        return {}
