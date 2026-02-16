
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from app.core.models import AgentState
from langgraph.types import interrupt
import json

class AskerNode:
    def __init__(self, llm):
        self.llm = llm # Expected: gemma3n:e4b
        
    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- DIAGNOSIS 4B: ASKER NODE ---")
        
        patient_info_dict = state.get("patient_info") or {}
        current_missing = state.get("missing_keys", [])
        
        if not current_missing:
            # Should not happen if routed correctly, but safe fallback
            return {}
            
        target_key = current_missing[0]
        print(f"DEBUG: Asking for '{target_key}'...")
        
        language = state.get("language", "English")
        
        # Generate Question
        formatted_question = await self.generate_question(patient_info_dict, current_missing, target_key, state["messages"], language)
        
        # --- HITL: Interrupt to get user answer ---
        # We ask the question via interrupt. The execution pauses here.
        user_answer = interrupt(formatted_question)
        
        # Resume Logic (Handle if answer is wrapped in dict by client/routes)
        if isinstance(user_answer, dict) and "interrupt_response" in user_answer:
            user_answer = user_answer["interrupt_response"]
            
        # Update State with Q & A
        return {
            "messages": [
                AIMessage(content=formatted_question),
                HumanMessage(content=user_answer)
            ]
        }

    async def generate_question(self, extracted_data, missing_keys, target_key, chat_history, language):
        lang_instruction = f"Language: {language}. YOU MUST REPLY IN {language} ONLY."
        
        system_prompt = """
        **Role:** Empathetic Medical Screener (Gemma 3)
        **Language Directive:** {lang_instruction}
        
        **Context:** 
        - Current Knowledge: {extracted_data}
        - Missing Information: {missing_keys}

        **Task:**
        1. Look at the target missing key: '{target_key}'.
        2. Ask **ONE** short, natural question to fill that missing gap.

        **Constraints:**
        - Maximum 15 words.
        - Do NOT repeat or acknowledge the user's previous answer. Just ask the question directly.
        - No "Robot Talk".
        - Do NOT provide translations in brackets.
        - Style: Conversational bridge.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history") 
        ])
        
        chain = prompt | self.llm
        
        res = await chain.ainvoke({
            "extracted_data": json.dumps(extracted_data, ensure_ascii=False),
            "missing_keys": missing_keys,
            "target_key": target_key,
            "chat_history": chat_history,
            "lang_instruction": lang_instruction
        })
        
        return res.content
