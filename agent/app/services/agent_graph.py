from typing import Dict, Any, List, Literal, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.core.config import settings
from app.core.models import AgentState
# IMPORT THE KNOWLEDGE MODULE
from app.core.medical_knowledge import analyze_input
import os

# Import Nodes
from app.workflow.med_friendly.nodes.thinking_node import ThinkingNode
from app.workflow.med_friendly.nodes.general_chat_node import GeneralChatNode
from app.workflow.med_friendly.nodes.interview_node import InterviewNode
from app.workflow.med_friendly.nodes.diagnosis_node import DiagnosisNode
from app.workflow.med_friendly.nodes.shopping_search_node import ShoppingSearchNode

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

        # Initialize Nodes
        self.thinking_node = ThinkingNode(self.llm)
        self.general_chat_node = GeneralChatNode(self.llm)
        self.interview_node = InterviewNode(self.llm)
        self.diagnosis_node = DiagnosisNode(self.llm_diagnosis)
        self.shopping_search_node = ShoppingSearchNode(self.llm, self.tavily_tool)

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

    # --- GRAPH ---
    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("thinking", self.thinking_node)
        workflow.add_node("general_chat", self.general_chat_node)
        workflow.add_node("interview", self.interview_node)
        workflow.add_node("diagnosis", self.diagnosis_node)
        workflow.add_node("shopping_search", self.shopping_search_node)

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

    @property
    def is_ready(self):
        return self.graph is not None and self.llm is not None

agent_service = AgentService()