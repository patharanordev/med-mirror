
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from app.core.models import AgentState, PatientInfo
from langchain_core.output_parsers import JsonOutputParser
import json

class EvaluationNode:
    def __init__(self, llm):
        self.llm = llm  # Expected: gemma3n:e4b
        
    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- DIAGNOSIS 4B: EVALUATION NODE ---")
        
        # 1. Initialize / Load State
        patient_info_dict = state.get("patient_info") or {}
        missing_keys = state.get("missing_keys")
        
        # Extract if strictly necessary (last msg is Human)
        # We only extract if the last message is from Human (answer to a question or initial input)
        last_message = state["messages"][-1]
        
        if isinstance(last_message, HumanMessage):
             print(f"DEBUG: Extracting info from '{last_message.content}'...")
             extracted = await self.extract_info(state["messages"], patient_info_dict)
             if extracted:
                print(f"DEBUG: Extracted: {extracted}")
                # Update extraction results
                patient_info_dict.update(extracted)
        
        # 2. Recalculate Missing Keys
        # We define the required keys based on PatientInfo fields
        required_keys = PatientInfo.__fields__.keys()
        
        current_missing = []
        for k in required_keys:
            val = patient_info_dict.get(k)
            # consider missing if None or empty string or "Unknown" / "None"
            if not val or val in ["", "None", "Unknown"]:
                current_missing.append(k)
        
        # Update State
        state["patient_info"] = patient_info_dict
        state["missing_keys"] = current_missing
        
        # If no missing keys, we prepare context for diagnosis
        context_str = self._format_patient_info(patient_info_dict)
        
        return {
            "patient_info": patient_info_dict,
            "missing_keys": current_missing,
            "context": context_str
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

    def _format_patient_info(self, info):
        lines = []
        for k, v in info.items():
            if v and v not in ["None", "Unknown"]:
                lines.append(f"- {k}: {v}")
        return "\n".join(lines)
