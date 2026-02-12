from typing import Dict, Any, List, Literal, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.core.config import settings
from app.core.models import AgentState
# IMPORT THE KNOWLEDGE MODULE
from app.core.medical_knowledge import analyze_input

# --- Structured Outputs ---
class ThinkingResult(BaseModel):
    analysis: str = Field(description="Extremely brief medical analysis.")
    todo: List[str] = Field(description="Plan of action.")
    next_step: Literal['general_chat', 'interview', 'diagnosis', 'shopping_search']

class MedicalExtraction(BaseModel):
    body_part: Optional[str] = Field(None, description="The affected body area (Face, Hair, Skin, etc).")
    duration: Optional[str] = Field(None, description="Time duration.")
    symptoms: Optional[str] = Field(None, description="Symptoms descriptions.")
    allergies: Optional[str] = Field(None, description="History of allergies.")
    shopping_interested: Optional[bool] = Field(None, description="True if user asks for products.")

class AgentService:
    def __init__(self):
        self.llm = ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            temperature=0, 
            streaming=True
        )
        
        self.tavily_tool = None
        try:
            if settings.TAVILY_API_KEY and "placeholder" not in settings.TAVILY_API_KEY:
                from langchain_community.tools.tavily_search import TavilySearchResults
                self.tavily_tool = TavilySearchResults(tavily_api_key=settings.TAVILY_API_KEY, max_results=3)
        except ImportError:
            pass

        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    async def warmup(self):
        try:
            await self.llm.ainvoke("hi")
            print("AGENT: LLM Warmup Complete.")
        except Exception as e:
            print(f"AGENT: LLM Warmup Failed: {e}")

    # --- NODE 1: THINKING (STRICT MEDICAL MODE) ---
    async def _thinking_node(self, state: AgentState, config: RunnableConfig):
        print("--- THINKING NODE ---")
        
        last_msg = state['messages'][-1].content
        analysis = analyze_input(last_msg)

        # HITL Guardrail: Immediate routing for detected idioms like "panda"
        if analysis['hints']:
            return {
                "todo": ["Identify symptoms from idiom"], 
                "next_step": "interview"
            }
        
        system_msg = "Route to 'interview' for medical/skin issues, else 'general_chat'."
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            MessagesPlaceholder("messages"),
        ])

        # .with_structured_output(ThinkingResult) returns a Pydantic object
        chain = (prompt | self.llm.with_structured_output(ThinkingResult)).with_config(
            {"run_name": "ThinkingChain"}
        )
        
        try:
            result = await chain.ainvoke(state, config=config)
            return {"todo": result.todo, "next_step": result.next_step}
        except Exception as e:
            # Fallback logic
            return {"next_step": "general_chat"}

    async def _general_chat_node(self, state: AgentState, config: RunnableConfig):
        prompt = ChatPromptTemplate.from_messages([
            ("system", settings.get_system_prompt()),
            ("system", "User is chatting casually. Be friendly. If they made a joke (like 'panda'), acknowledge it but ask if they have skin/hair concerns."),
            MessagesPlaceholder("messages"),
        ])
        response = await (prompt | self.llm).ainvoke(state, config=config)
        return {"messages": [response]}

    async def _interview_node(self, state: AgentState, config: RunnableConfig):
        last_message = state['messages'][-1].content
        analysis = analyze_input(last_message)
        
        extract_prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract medical data (Body Part, Symptoms, Duration, Allergies)."),
            ("human", last_message)
        ])
        extractor = extract_prompt | self.llm.with_structured_output(MedicalExtraction)
        data = await extractor.ainvoke({})
        
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        current_state = {**state, **updates}

        questions = {
            "body_part": "Which part of the body is affected? (e.g., face, arms)",
            "symptoms": "What are your symptoms? (e.g., itchy, painful, or just dark spots)",
            "duration": "How many days have you had this?",
            "allergies": "Do you have any history of drug allergies?"
        }
            
        for field, question in questions.items():
            if not current_state.get(field):
                # Return ONLY the short question and stop (HITL)
                return {**updates, "messages": [AIMessage(content=question)]}
    
        return updates

    async def _diagnosis_node(self, state: AgentState, config: RunnableConfig):
        # Added a strict "Concise" instruction to the system prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", settings.get_system_prompt()),
            ("system", "Concise summary: Provide 1 sentence for the possible cause and exactly 2 short bullet points for care instructions."),
            MessagesPlaceholder("messages")
        ])
        
        inputs = {
            "messages": state['messages'],
            "symptoms": state.get("symptoms", "initial symptoms"),
            "body_part": state.get("body_part", "affected area"),
            "duration": state.get("duration", "duration"),
            "allergies": state.get("allergies", "none"),
            "context": state.get("context", "No additional information")
        }
        
        try:
            response = await (prompt | self.llm).ainvoke(inputs, config=config)
            return {"messages": [response], "diagnosis": response.content}
        except Exception as e:
            print(f"Diagnosis Node Error: {e}")
            # Fallback response if the prompt still fails
            fallback_msg = AIMessage(content="ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่อีกครั้ง")
        return {"messages": [fallback_msg]}

    async def _shopping_search_node(self, state: AgentState, config: RunnableConfig):
        query = f"products for {state.get('symptoms', 'skin')} on {state.get('body_part', 'body')}"
        
        if self.tavily_tool:
            results = await self.tavily_tool.ainvoke(query)
            content = str(results)
        else:
            content = "Search unavailable."
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", settings.get_system_prompt()),
            ("system", "Recommend products based on these search results:"),
            ("user", content)
        ])
        
        # FIX: Pass context here as well
        inputs = {
            "context": state.get("context", "No context"),
        }
        
        response = await (prompt | self.llm).ainvoke(inputs, config=config)
        return {"messages": [response]}

    # --- GRAPH ---
    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("thinking", self._thinking_node)
        workflow.add_node("general_chat", self._general_chat_node)
        workflow.add_node("interview", self._interview_node)
        workflow.add_node("diagnosis", self._diagnosis_node)
        workflow.add_node("shopping_search", self._shopping_search_node)

        workflow.set_entry_point("thinking")
        
        workflow.add_conditional_edges("thinking", lambda x: x['next_step'], 
            {"general_chat": "general_chat", "interview": "interview", 
             "diagnosis": "diagnosis", "shopping_search": "shopping_search"})
        
        def route_interview(state):
            if all([state.get("body_part"), state.get("symptoms"), state.get("duration"), state.get("allergies")]):
                return "diagnosis"
            return END
            
        workflow.add_conditional_edges("interview", route_interview, {"diagnosis": "diagnosis", END: END})
        workflow.add_edge("general_chat", END)
        workflow.add_edge("diagnosis", END)
        workflow.add_edge("shopping_search", END)

        return workflow.compile(checkpointer=self.checkpointer)

    def get_graph(self):
        return self.graph

agent_service = AgentService()