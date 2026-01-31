from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, BaseMessage
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
1. ถามคำถามที่เป็นประโยชน์ต่อการวินิจฉัย เช่น ระยะเวลาที่เป็น, อาการคัน/เจ็บ, ประวัติการแพ้ยา
2. ถามทีละคำถาม อย่ายิงคำถามรัว
3. ใช้ภาษาไทยที่สุภาพ แต่มืออาชีพ
4. หากข้อมูลเพียงพอแล้ว ให้สรุปคำแนะนำเบื้องต้น และแนะนำให้ไปพบแพทย์ (อย่าฟันธงการรักษาเอง)

เริ่มการสนทนาโดยอ้างอิงถึงสิ่งที่ตรวจพบในภาพ
"""

class AgentService:
    def __init__(self):
        self.llm = ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            streaming=True
        )
        self.graph = self._build_graph()

    def _call_model(self, state: AgentState):
        messages = state['messages']
        context = state.get('context', 'ไม่ระบุ')
        
        # Check if system message exists, if not prepend it
        if not messages or not isinstance(messages[0], SystemMessage):
            system_msg = SystemMessage(content=SYSTEM_TEMPLATE.format(context=context))
            messages = [system_msg] + messages
        else:
            # Update context in system prompt if needed
            messages[0] = SystemMessage(content=SYSTEM_TEMPLATE.format(context=context))
        
        response = self.llm.invoke(messages)
        return {"messages": [response]}

    def _build_graph(self) -> CompiledStateGraph:
        workflow = StateGraph(AgentState)
        
        workflow.add_node("agent", self._call_model)
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)
        
        return workflow.compile()

    def get_graph(self) -> CompiledStateGraph:
        return self.graph

# Singleton instance to be used by dependencies
agent_service = AgentService()
