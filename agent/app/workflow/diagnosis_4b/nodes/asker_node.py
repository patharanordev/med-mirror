
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from app.core.models import AgentState
from langgraph.types import interrupt
from app.core.models import PatientInfo
import json

class AskerNode:
    def __init__(self, llm):
        self.llm = llm # Expected: gemma3n:e4b
        self.field_guidance = {
            name: field.field_info.description 
            for name, field in PatientInfo.__fields__.items()
        }
        
    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- DIAGNOSIS 4B: ASKER NODE ---")
        
        patient_info_dict = state.get("patient_info") or {}
        current_missing = state.get("missing_keys", [])
        
        if len(current_missing) == 0:
            return {"missing_keys": []}
            
        target_keys = current_missing[:2] # Ask for up to 2 missing keys at a time
        target_keys_str = ", ".join(target_keys)
        print(f"DEBUG: Asking for '{target_keys_str}'...")
        
        language = state.get("language", "English")
        
        # Generate Question
        formatted_question = await self.generate_question(patient_info_dict, current_missing, target_keys, state["messages"], language)
        
        if not formatted_question or not formatted_question.strip():
            print(f"WARNING: AskerNode generated empty question for '{target_keys_str}'. Dropping keys to avoid loop.")
            # Remove the problematic keys so evaluation can proceed without them
            remaining = [k for k in current_missing if k not in target_keys]
            return {"missing_keys": remaining}

        
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

    async def generate_question(self, extracted_data, missing_keys, target_keys, chat_history, language):
        lang_instruction = f"Language: {language}. YOU MUST REPLY IN {language} ONLY."
        
        target_keys_str = ", ".join(target_keys)
        specific_hints = [f"- {key}: {self.field_guidance.get(key, 'Ask about this medical detail.')}" for key in target_keys]
        hints_str = "\n".join(specific_hints)

        system_prompt = """<role>Empathetic Medical Screener</role>
<language>{lang_instruction}</language>

<context>
  <current_knowledge>{extracted_data}</current_knowledge>
  <missing_information>{missing_keys}</missing_information>
</context>

<goal>Help the doctor screen the patient's symptoms to scope down the diagnosis and reduce the doctor's burden. The question should cover all possibilities related to the missing information efficiently.</goal>

<task>
  1. Look at the target missing keys: {target_keys}.
  2. Ask ONE smart, natural, and open-ended question that seamlessly combines and asks for these missing gaps.
  3. Ensure the question is easy for the patient to answer in one go without feeling overwhelmed.
  4. Specific hints for target keys:
  <hints>
{hints_str}
  </hints>
</task>

<constraints>
  - Maximum 30 words.
  - NEGATIVE: Do NOT ask Yes/No questions. Ask open-ended questions (e.g. "How long...", "Describe...", "Where...").
  - NEGATIVE: NEVER repeat or acknowledge the user's previous answer.
  - NEGATIVE: Do NOT start with "Okay", "I understand", "Got it".
  - NEGATIVE: Do NOT say "Thank you" or any closing statement.
  - NEGATIVE: Do NOT provide translations in brackets.
  - NEGATIVE: Do NOT make assumptions or inferences about the answer. Ask directly for the fact (e.g. ask "How many hours do you sleep?" NOT "You seem to sleep very little, right?").
  - CRITICAL: You MUST end with a question mark (?).
  - CRITICAL: You MUST ask a question related to: {target_keys}.
  - Start the question IMMEDIATELY.
  - No robot talk. Direct and warm tone.
  - Style: Concise, connected, and smart.
</constraints>"""

        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history") 
        ])
        
        chain = prompt | self.llm
        
        res = await chain.ainvoke({
            "extracted_data": json.dumps(extracted_data, ensure_ascii=False),
            "missing_keys": missing_keys,
            "target_keys": target_keys_str,
            "chat_history": chat_history,
            "lang_instruction": lang_instruction,
            "hints_str": hints_str
        })
        
        return res.content
