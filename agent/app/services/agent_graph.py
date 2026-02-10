from typing import Dict, Any, List, Sequence, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

# Tools
try:
    from langchain_community.tools.tavily_search import TavilySearchResults
except ImportError:
    TavilySearchResults = None
    print("WARNING: langchain_community or tavily-python not installed. Shopping search will be mocked.")

from app.core.config import settings
from app.core.models import AgentState

# --- Structured Output Models ---
class MedicalInfo(BaseModel):
    duration: Optional[str] = Field(None, description="Duration of the skin condition (e.g., '2 days', '1 week').")
    symptoms: Optional[str] = Field(None, description="Symptoms descriptions (e.g., 'itching', 'pain', 'redness').")
    allergies: Optional[str] = Field(None, description="History of allergies (e.g., 'none', 'penicillin').")
    shopping_interested: Optional[bool] = Field(None, description="Whether the user is interested in product recommendations.")

class AgentService:
    def __init__(self):
        self.llm = ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            streaming=True
        )
        
        # Tools
        # Tools
        # Check if key is valid (not placeholder)
        if TavilySearchResults and settings.TAVILY_API_KEY and "placeholder" not in settings.TAVILY_API_KEY:
            self.tavily_tool = TavilySearchResults(tavily_api_key=settings.TAVILY_API_KEY, max_results=3)
        else:
            print("AGENT: Tavily API Key missing or placeholder. Shopping search will be mocked.")
            self.tavily_tool = None

        # System Prompt for "Persona"
        self.system_prompt = settings.get_system_prompt()
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()
        self.is_ready = False

    async def warmup(self):
        """Forces LLM to load model into VRAM."""
        print("AGENT: Warming up LLM...")
        try:
            await self.llm.ainvoke("hi")
            self.is_ready = True
            print("AGENT: LLM Warmup Complete (Ready). 🧠")
        except Exception as e:
            print(f"AGENT: LLM Warmup Failed: {e}")

    def _gen_multimodal_message(self, text: str, image_url: str) -> HumanMessage:
        return HumanMessage(
            content=[
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": text},
            ]
        )

    # --- Nodes ---

    async def _interview_node(self, state: AgentState, config: RunnableConfig):
        """
        Node: Interview (Input Validation Pattern)
        Extracts duration, symptoms, allergies from conversation.
        Asks specifically for missing information.
        """
        messages = state['messages']
        # If user just sent a message, try to extract info
        if messages and isinstance(messages[-1], HumanMessage):
            # Extraction Logic using LLM
            extract_prompt = ChatPromptTemplate.from_messages([
                ("system", "Extract the following medical info from the user's latest message if present. Return null if not found."),
                ("human", "{text}")
            ])
            # Use structured output to update state fields
            structured_llm = self.llm.with_structured_output(MedicalInfo)
            chain = extract_prompt | structured_llm
            extraction = await chain.ainvoke({"text": messages[-1].content})
            
            # Update state only if new info found
            updates = {}
            if extraction.duration: updates['duration'] = extraction.duration
            if extraction.symptoms: updates['symptoms'] = extraction.symptoms
            if extraction.allergies: updates['allergies'] = extraction.allergies
            if extraction.shopping_interested is not None: updates['shopping_interested'] = extraction.shopping_interested
            
            # Apply updates locally for decision making (state will be updated by return)
            state.update(updates)
        else:
            updates = {}

        # Decide what to ask next
        missing = []
        if not state.get('duration'): missing.append("duration (how long has it been?)")
        if not state.get('symptoms'): missing.append("symptoms (itching, pain?)")
        if not state.get('allergies'): missing.append("allergies (any history?)")

        if missing:
            # Generate a question for the missing info
            ask_prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                MessagesPlaceholder("messages"),
                ("system", f"The user has not provided: {', '.join(missing)}. Ask politely for ONE of these.")
            ])
            chain = ask_prompt | self.llm
            response = await chain.ainvoke({"messages": messages, "context": state.get('context')}, config=config)
            return {**updates, "messages": [response]}
        else:
            # All info present, pass through (next node will handle diagnosis)
            # We don't return message here if we are transitioning immediately, 
            # but usually we want to acknowledge receipt?
            # Actually, we can return updates and let condition move to diagnosis.
            return updates

    async def _diagnosis_node(self, state: AgentState, config: RunnableConfig):
        """
        Node: Diagnosis
        Generates analysis based on collected info.
        """
        diag_prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("system", "Context: {context}. Duration: {duration}. Symptoms: {symptoms}. Allergies: {allergies}."),
            MessagesPlaceholder("messages"),
            ("system", "Provide a preliminary analysis/recommendation based on the above. Warn that this is not a doctor's diagnosis.")
        ])
        chain = diag_prompt | self.llm
        response = await chain.ainvoke(state, config=config)
        
        return {"messages": [response], "diagnosis": response.content}

    async def _shopping_proposal_node(self, state: AgentState, config: RunnableConfig):
        """
        Node: Shopping Proposal
        Asks if the user wants product recommendations.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("system", "Ask the user politely if they want you to recommend suitable skin care products from the internet (e.g. 'ยาทาผิว') based on their diagnosis.")
        ])
        chain = prompt | self.llm
        response = await chain.ainvoke(state, config=config)
        return {"messages": [response]}

    async def _shopping_search_node(self, state: AgentState, config: RunnableConfig):
        """
        Node: Shopping Search (HITL: Action)
        Searches Tavily for products and summarizes.
        """
        query = f"skin care product for {state.get('diagnosis', 'skin condition')} {state.get('symptoms', '')}"
        print(f"AGENT: Searching Tavily for: {query}")
        
        search_content = ""
        if self.tavily_tool:
            try:
                results = await self.tavily_tool.ainvoke(query)
                # Format raw results for LLM
                search_content = "Here are the search results:\n"
                for res in results[:4]:
                    search_content += f"- Name/Url: {res.get('url')} Content: {res.get('content')}\n"
            except Exception as e:
                search_content = f"Search failed: {e}"
        else:
            search_content = "Search tool is not configured."
            
        # Summarize with LLM
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("system", "You have performed a product search. Summarize the following results for the user and recommend checking them out. If search failed, apologize."),
            ("user", "{search_results}")
        ])
        chain = summary_prompt | self.llm
        response = await chain.ainvoke({"search_results": search_content}, config=config)
        
        return {"messages": [response]}

    # --- Edges ---

    def _should_continue_interview(self, state: AgentState):
        """Edge: Check if we have all diagnostic info."""
        if state.get('duration') and state.get('symptoms') and state.get('allergies'):
            return "diagnosis"
        return END  # Effectively waits for user input

    def _build_graph(self) -> CompiledStateGraph:
        workflow = StateGraph(AgentState)
        
        workflow.add_node("interview", self._interview_node)
        workflow.add_node("diagnosis", self._diagnosis_node)
        workflow.add_node("shopping_proposal", self._shopping_proposal_node)
        workflow.add_node("shopping_search", self._shopping_search_node)
        
        # Entry Point
        workflow.set_entry_point("interview")

        # Routing logic
        workflow.add_conditional_edges(
            "interview",
            self._route_after_interview,
             {
                 "diagnosis": "diagnosis",
                 "shopping_search": "shopping_search",
                 END: END
             }
        )
        
        workflow.add_edge("diagnosis", "shopping_proposal")
        workflow.add_edge("shopping_proposal", END) # Wait for approval
        workflow.add_edge("shopping_search", END)
        
        return workflow.compile(checkpointer=self.checkpointer)

    def _route_after_interview(self, state: AgentState):
        # 1. If we have diagnosis, we are in the "Shopping Phase"
        if state.get("diagnosis"):
            # We are expecting a Yes/No for shopping
            messages = state['messages']
            if messages and isinstance(messages[-1], HumanMessage):
                text = messages[-1].content.lower()
                # Heuristic for "Yes" in English and Thai
                if any(x in text for x in ["yes", "ok", "sure", "please", "เอา", "สนใจ", "ครับ", "ค่ะ", "search"]):
                    return "shopping_search"
            # If no (or unclear), just End (Chat loop)
            return END
        
        # 2. If no diagnosis, check if info complete
        if state.get('duration') and state.get('symptoms') and state.get('allergies'):
            return "diagnosis"
            
        # 3. Info incomplete -> Wait for input
        return END

    def get_graph(self) -> CompiledStateGraph:
        return self.graph

# Singleton instance
agent_service = AgentService()
