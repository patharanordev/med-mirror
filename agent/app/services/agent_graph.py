from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from app.core.config import settings
import os
import asyncio

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
            streaming=True,
            max_tokens=2048
        )
        
        self.tavily_tool = None
        try:
            if settings.TAVILY_API_KEY and "placeholder" not in settings.TAVILY_API_KEY:
                from langchain_community.tools.tavily_search import TavilySearchResults
                self.tavily_tool = TavilySearchResults(tavily_api_key=settings.TAVILY_API_KEY, max_results=3)
        except ImportError:
            pass

        self.checkpointer = MemorySaver()
        
        # Load Workflow based on environment variable
        self.active_workflow = os.getenv("ACTIVE_WORKFLOW", "med_gemma_4b")
        print(f"AGENT: Loading workflow '{self.active_workflow}'...")
        
        if self.active_workflow == "med_gemma_27b":
            from app.workflow.med_gemma_27b.graph import build_graph
        elif self.active_workflow == "med_gemma_4b":
            from app.workflow.med_gemma_4b.graph import build_graph
        else:
            raise ValueError(f"Unknown workflow: {self.active_workflow}")
            
        self.graph = build_graph(self.llm, self.llm_diagnosis, self.checkpointer, self.tavily_tool)
        
        if not os.path.exists("output"):
            os.mkdir("output")
        try:
            image = self.graph.get_graph().draw_mermaid_png()
            with open("output/graph.png", "wb") as f:
                f.write(image)
        except Exception:
            pass

    async def warmup(self):
        print("AGENT: Starting Comprehensive Warmup...")
        
        async def warm_main_llm():
            try:
                # Warm up the graph (Thinking Node is usually entry)
                print("AGENT: Warming up Main Graph (Thinking Node)...")
                dummy_state = {
                    "messages": [HumanMessage(content="hi")],
                    "context": "Warmup context"
                }
                config = {"configurable": {"thread_id": "warmup"}}
                # Just run one step or invoke
                # We use ainvoke but we need to handle the stream or result.
                # Since we just want to wake it up, running it is enough.
                # However, we must be careful not to trigger a long conversation loop.
                # But ThinkingNode usually returns a plan and stops or goes to next.
                # Let's just invoke.
                await self.graph.ainvoke(dummy_state, config=config)
                print("AGENT: Main Graph Warmup Complete.")
            except Exception as e:
                print(f"AGENT: Main Graph Warmup Failed: {e}")

        async def warm_diagnosis_llm():
            try:
                print("AGENT: Warming up Diagnosis LLM...")
                await self.llm_diagnosis.ainvoke("hi")
                print("AGENT: Diagnosis LLM Warmup Complete.")
            except Exception as e:
                print(f"AGENT: Diagnosis LLM Warmup Failed: {e}")

        # Run both warmups in parallel
        await asyncio.gather(warm_main_llm(), warm_diagnosis_llm())
        print("AGENT: All Models Warmup Complete.")

    def get_graph(self):
        return self.graph

    @property
    def is_ready(self):
        return self.graph is not None and self.llm is not None

agent_service = AgentService()