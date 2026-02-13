from typing import Dict, Any, List, Literal, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from pydantic.v1 import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.core.config import settings
from app.core.models import AgentState
# IMPORT THE KNOWLEDGE MODULE
from app.core.medical_knowledge import analyze_input
import os

# --- Structured Outputs ---
class ThinkingResult(BaseModel):
    analysis: str = Field(description="Extremely brief medical analysis.")
    todo: List[str] = Field(description="Plan of action. Must be a list of 5-10 concise bullet points.")
    next_step: Literal['general_chat', 'interview', 'diagnosis', 'shopping_search']

class QuestionResult(BaseModel):
    question: str = Field(description="A single, concise (max 1-2 sentences), and smart question to ask the user.")

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

        self.llm_diagnosis = ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL_DIAGNOSIS,
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
        
        if not os.path.exists("output"):
            os.mkdir("output")
        image = self.graph.get_graph().draw_mermaid_png()
        with open("output/graph.png", "wb") as f:
            f.write(image)

    async def warmup(self):
        try:
            await self.llm.ainvoke("hi")
            print("AGENT: LLM Warmup Complete.")
        except Exception as e:
            print(f"AGENT: LLM Warmup Failed: {e}")

    # --- NODE 1: THINKING (ROUTER) ---
    async def _thinking_node(self, state: AgentState, config: RunnableConfig):
        print("--- THINKING NODE ---")
        
        last_msg = state['messages'][-1].content
        
        # 1. System Prompt for Routing
        system_msg = """You are the 'Brain' of MedMirror. 
        Decide the next step based on the user's input.
        
        Routing Rules:
        - 'general_chat': Greetings, small talk, jokes, or non-medical questions.
        - 'interview': User mentions a body part, symptom, or problem (e.g., "my face is red", "panda eyes").
        - 'shopping_search': User explicitly asks to BUY products or RECOMENDATIONS for products.
        - 'diagnosis': (Rarely used directly) Only if ALL info (symptoms, duration, allergies) is present.

        Task: Generate a 'todo' list with 2-5 specific steps for the next stage (e.g., "Ask about duration", "Check for allergies", "Analyze symptom severity").

        Context: {context}
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            MessagesPlaceholder("messages"),
        ])

        # .with_structured_output(ThinkingResult) returns a Pydantic object
        chain = (prompt | self.llm.with_structured_output(ThinkingResult)).with_config(
            {"run_name": "ThinkingChain"}
        )
        
        try:
            # Inject context into state for the thinking node
            input_state = {**state, "context": state.get("context", "No context")}
            result = await chain.ainvoke(input_state, config=config)
            return {"todo": result.todo, "next_step": result.next_step}
        except Exception as e:
            # Fallback logic
            print(f"Thinking Error: {e}")
            return {"next_step": "general_chat"}

    async def _general_chat_node(self, state: AgentState, config: RunnableConfig):
        prompt = ChatPromptTemplate.from_messages([
            ("system", settings.get_system_prompt()),
            ("system", "Keep it short (1-2 sentences). Be smart & witty."),
            MessagesPlaceholder("messages"),
        ])
        chain = prompt | self.llm
        response = await chain.ainvoke(state, config=config.copy() | {"run_name": "GeneralChatChain"})
        return {"messages": [response]}

    async def _interview_node(self, state: AgentState, config: RunnableConfig):
        last_message = state['messages'][-1].content
        
        extract_prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract: Body Part, Duration, Symptoms, Allergies. Return None if not found."),
            ("human", last_message)
        ])
        extractor = (extract_prompt | self.llm.with_structured_output(MedicalExtraction)).with_config(
            {"run_name": "InterviewExtractionChain"}
        )
        data = await extractor.ainvoke({})
        
        # Merge new data
        if data:
            updates = {k: v for k, v in data.dict().items() if v is not None}
        else:
            updates = {}
        current_state = {**state, **updates}

        # Check for missing fields
        required_fields = ["body_part", "symptoms", "duration", "allergies"]
        missing_fields = [f for f in required_fields if not current_state.get(f)]

        if missing_fields:
            next_field = missing_fields[0]
            
            # Dynamic Question Generation
            q_system = settings.get_system_prompt()
            q_prompt = ChatPromptTemplate.from_messages([
                ("system", q_system),
                ("system", f"Ask a SHORT, SMART question to get the '{next_field}'. Only ONE question. Max 1-2 sentences."),
                MessagesPlaceholder("messages")
            ])
            
            # Using with_structured_output for safety, or just plain string
            q_chain = (q_prompt | self.llm.with_structured_output(QuestionResult)).with_config(
               {"run_name": "InterviewAskChain"}
            )
            
            q_result = await q_chain.ainvoke(state, config=config)
            return {**updates, "messages": [AIMessage(content=q_result.question)]}
    
        return updates

    async def _diagnosis_node(self, state: AgentState, config: RunnableConfig):
        # Added a strict "Concise" instruction to the system prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", settings.get_system_prompt()),
            ("system", "CONCLUSION: 1-2 sentences diagnosis maximum. CARE: 2 short bullet points. TOTAL: 3-4 lines max."),
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
            chain = (prompt | self.llm_diagnosis).with_config({"run_name": "DiagnosisChain"})
            response = await chain.ainvoke(inputs, config=config)
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
            ("system", "Recommend products based on these search results. keep it concise (max 1-2 sentences with list of products)."),
            ("user", content)
        ])
        
        # FIX: Pass context here as well
        inputs = {
            "context": state.get("context", "No context"),
        }
        
        
        chain = (prompt | self.llm).with_config({"run_name": "ShoppingSummarizeChain"})
        response = await chain.ainvoke(inputs, config=config)
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