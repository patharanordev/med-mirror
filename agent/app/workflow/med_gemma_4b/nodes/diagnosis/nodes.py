from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from app.core.models import AgentState, PatientInfo
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser
import json

class AskerNode:
    def __init__(self, llm):
        self.llm = llm
        
    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- DIAGNOSIS SUBGRAPH: ASKER NODE ---")
        
        # 1. Initialize / Load State
        patient_info_dict = state.get("patient_info") or {}
        missing_keys = state.get("missing_keys")
        
        # Extract if strictly necessary (last msg is Human)
        last_message = state["messages"][-1]
        if isinstance(last_message, HumanMessage):
             print(f"DEBUG: Extracting info from '{last_message.content}'...")
             extracted = await self.extract_info(state["messages"], patient_info_dict)
             if extracted:
                print(f"DEBUG: Extracted: {extracted}")
                patient_info_dict.update(extracted)
        
        # 2. Recalculate Missing Keys
        # We define the required keys based on PatientInfo fields
        required_keys = PatientInfo.__fields__.keys()
        
        current_missing = []
        for k in required_keys:
            val = patient_info_dict.get(k)
            # consider missing if None or empty string
            if not val or val in ["", "None", "Unknown"]:
                current_missing.append(k)
        
        # Update State
        state["patient_info"] = patient_info_dict
        state["missing_keys"] = current_missing
        
        # 3. Check Condition
        if not current_missing:
            print("DIAGNOSIS INTERVIEW COMPLETE.")
            # Prepare context for Diagnosis Node
            context_str = self._format_patient_info(patient_info_dict)
            return {
                "patient_info": patient_info_dict,
                "missing_keys": [],
                "diagnosis_complete": True,
                "context": context_str # Update context for diagnosis node
            }
            
        # 4. Generate Question (Adaptive Asker)
        target_key = current_missing[0]
        print(f"DEBUG: Asking for '{target_key}'...")
        
        language = state.get("language", "English")
        formatted_question = await self.generate_question(patient_info_dict, current_missing, target_key, state["messages"], language)
        
        return {
            "patient_info": patient_info_dict,
            "missing_keys": current_missing,
            "diagnosis_complete": False,
            "messages": [AIMessage(content=formatted_question)]
        }

    async def extract_info(self, chat_history, current_data):
        system_prompt = """You are a medical data extractor. 
        Analyze the conversation and extract patient information into JSON format.
        
        CRITICAL INSTRUCTION:
        - You MUST look at the *previous question* from the AI to understand the user's answer.
        - If the AI asked "When did it start?" and the user says "2 years", extract "2 years" as 'onset_and_duration'.
        - If the AI asked "Where is it?" and user says "Face", extract "Face" as 'location_and_spread'.
        
        Update the current knowledge. Only fields that are explicitly mentioned or implied by the answer to the last question should be updated.
        If a field is not mentioned, do NOT include it in the JSON (or keep as null).
        
        Current Knowledge: {current_data}
        
        Output Schema:
        {format_instructions}
        """
        
        parser = JsonOutputParser(pydantic_object=PatientInfo)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
        ])
        
        chain = prompt | self.llm | parser
        
        try:
            res = await chain.ainvoke({
                "chat_history": chat_history, 
                "current_data": json.dumps(current_data, ensure_ascii=False),
                "format_instructions": parser.get_format_instructions()
            })
            return res
        except Exception as e:
            print(f"Extraction Error: {e}")
            return {}

    async def generate_question(self, extracted_data, missing_keys, target_key, chat_history, language):
        # Use detecting language from ThinkingNode/State
        lang_instruction = f"Language: {language}. YOU MUST REPLY IN {language} ONLY."
        
        # Adaptive Asker Gemma 3 Optimized Prompt
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
            # We might strictly not need history here if extracted_data is enough, 
            # but history helps with "Acknowledge previous answer".
            # Let's include just the last message maybe? Or full history?
            # User example showed "Acknowledge the patient's last statement".
            MessagesPlaceholder("chat_history") 
        ])
        
        # We need to filter history to avoid confusing the model with its own previous thoughts?
        # Actually standard history is fine.
        
        chain = prompt | self.llm
        
        res = await chain.ainvoke({
            "extracted_data": json.dumps(extracted_data, ensure_ascii=False),
            "missing_keys": missing_keys,
            "target_key": target_key,
            "chat_history": chat_history,
            "lang_instruction": lang_instruction
        })
        
        return res.content

    def _format_patient_info(self, info):
        lines = []
        for k, v in info.items():
            if v and v not in ["None", "Unknown"]:
                lines.append(f"- {k}: {v}")
        return "\n".join(lines)
