from typing import Dict, Any, List, Sequence
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from app.core.config import settings
from app.core.models import AgentState

# --- System Prompt (Thai) ---
SYSTEM_TEMPLATE = """
คุณคือผู้ช่วยทางการแพทย์อัจฉริยะ 'MedMirror AI'
หน้าที่ของคุณคือการสัมภาษณ์ผู้ป่วยเพื่อขอข้อมูลเพิ่มเติมเกี่ยวกับอาการทางผิวหนังที่ตรวจพบ

บริบทจากการตรวจจับภาพ: {context}

คำแนะนำ:
1. หากมีรูปภาพแนบมา ให้วิเคราะห์สิ่งที่เห็นในภาพด้วย (คุณมีความสามารถในการมองเห็น)
2. ถามคำถามที่เป็นประโยชน์ต่อการวินิจฉัย เช่น ระยะเวลาที่เป็น, อาการคัน/เจ็บ, ประวัติการแพ้ยา
3. ถามทีละคำถาม อย่ายิงคำถามรัว
4. ใช้ภาษาไทยที่สุภาพ แต่มืออาชีพ
5. หากข้อมูลเพียงพอแล้ว ให้สรุปคำแนะนำเบื้องต้น และแนะนำให้ไปพบแพทย์ (อย่าฟันธงการรักษาเอง)

หากคุณได้รับรูปภาพ กรุณารับทราบและอ้างอิงถึงสิ่งที่เห็นด้วย
"""

class AgentService:
    def __init__(self):
        self.llm = ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            streaming=True
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_TEMPLATE),
            MessagesPlaceholder(variable_name="messages"),
        ])
        self.graph = self._build_graph()
        self.is_ready = False

    async def warmup(self):
        """Forces LLM to load model into VRAM."""
        print("AGENT: Warming up LLM (Ollama)...")
        try:
            # Simple dummy invocation
            await self.llm.ainvoke("hi")
            self.is_ready = True
            print("AGENT: LLM Warmup Complete (Ready). 🧠")
        except Exception as e:
            print(f"AGENT: LLM Warmup Failed: {e}")

    def _gen_multimodal_message(self, text: str, image_url: str) -> HumanMessage:
        """Constructs a multimodal human message following OpenAI/LangChain best practices."""
        print(f"DEBUG: Constructing multimodal message. Image length: {len(image_url)}")
        return HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
                {"type": "text", "text": text},
            ]
        )

    async def _call_model(self, state: AgentState, config: RunnableConfig):
        """Node to call the LLM with the current state."""
        messages = list(state['messages'])
        context = state.get('context', 'ไม่ระบุ')
        image_url = state.get('image_url')

        print(f"DEBUG: Calling model {settings.LLM_MODEL}. Image present: {bool(image_url)}")

        # If we have an image and the last message is a HumanMessage with just text, 
        # convert it to multimodal for the LLM call.
        if image_url and len(messages) > 0:
            last_message = messages[-1]
            if isinstance(last_message, HumanMessage) and isinstance(last_message.content, str):
                messages[-1] = self._gen_multimodal_message(last_message.content, image_url)

        # Build chain: Prompt | LLM
        chain = self.prompt | self.llm
        
        # Invoke LLM with the passed config (propagates callbacks/streaming)
        response = await chain.ainvoke({
            "messages": messages,
            "context": context
        }, config=config)
        
        # Return new message to be added to state via Annotated[..., add_messages]
        return {"messages": [response]}

    def _build_graph(self) -> CompiledStateGraph:
        """Construct the LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("agent", self._call_model)
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)
        
        return workflow.compile()

    def get_graph(self) -> CompiledStateGraph:
        """Get the compiled graph executable."""
        return self.graph

# Singleton instance
agent_service = AgentService()
