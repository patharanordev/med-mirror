from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from app.core.config import settings
from app.core.models import AgentState

class DiagnosisNode:
    def __init__(self, llm):
        self.llm = llm

    async def __call__(self, state: AgentState, config: RunnableConfig):
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
            chain = (prompt | self.llm).with_config({"run_name": "DiagnosisChain"})
            response = await chain.ainvoke(inputs, config=config)
            return {"messages": [response], "diagnosis": response.content}
        except Exception as e:
            print(f"Diagnosis Node Error: {e}")
            # Fallback response if the prompt still fails
            fallback_msg = AIMessage(content="ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่อีกครั้ง")
            return {"messages": [fallback_msg]}
