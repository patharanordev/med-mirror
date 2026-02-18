
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from app.core.models import AgentState, PatientInfo
from langchain_core.output_parsers import JsonOutputParser
import json

class EvaluationNode:
    def __init__(self, llm):
        self.llm = llm  # Expected: gemma3n:e4b
        self.valid_keys = list(PatientInfo.__fields__.keys())
        
    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- DIAGNOSIS 4B: EVALUATION NODE ---")
        
        # 1. Initialize / Load State
        patient_info_dict = state.get("patient_info") or {}
        
        # Extract if strictly necessary (last msg is Human)
        # We only extract if the last message is from Human (answer to a question or initial input)
        last_message = state["messages"][-1]
        
        if isinstance(last_message, HumanMessage):
             print(f"DEBUG: Extracting info from '{last_message.content}'...")
             extracted = await self.extract_info(state["messages"], patient_info_dict)
             if extracted:
                print(f"DEBUG: Extracted: {extracted}")
                # Update extraction results
                cleaned_extracted = {k: v for k, v in extracted.items() if k in self.valid_keys}
                patient_info_dict.update(cleaned_extracted)
        
        # 2. Recalculate Missing Keys
        current_missing = []
        for k in self.valid_keys:
            val = patient_info_dict.get(k)
            # consider missing if None or empty string or "Unknown" / "None"
            if val is None or str(val).strip() == "__MISSING__":
                current_missing.append(k)
        
        if len(current_missing) == 0:
            return {
                "patient_info": state["patient_info"],
                "missing_keys": current_missing,
                "context": state["context"]
            }
        
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
        keys_string = ", ".join(self.valid_keys)
        # system_prompt = """You are a medical data extractor. 
        # Analyze the conversation and extract patient information into JSON format.
        
        # CRITICAL INSTRUCTION:
        # - CONTEXT AWARENESS: Always look at the AI's last question to understand the User's reply.
        # - NEGATIVE ANSWERS: If the user explicitly says "No", "None", "Don't know", or "Not sure" (ไม่มี, ไม่รู้, ไม่แน่ใจ), you MUST fill the field with "None" or "Unknown"(for not sure) instead of leaving it null.
        # - NO HALLUCINATION: Use ONLY the keys provided in the schema. Never invent new keys.
        # - DEDUPLICATION: If information is already present in 'current_data', do not change it unless the user provides a direct update.

        # Update the current knowledge. Only fields that are explicitly mentioned or implied by the answer to the last question should be updated.
        # If a field is not mentioned both current conversation and chat history, keep as "__MISSING__".

        # <ChatHistory>
        # {chat_history}
        # </ChatHistory>

        # <AllowedKeys>
        # [{keys_string}]
        # </AllowedKeys>
        
        # <CurrentKnowledge>{current_data}</CurrentKnowledge>
        # <OutputSchema>{format_instructions}</OutputSchema>
        # """

        system_prompt = """You are a precise medical data extractor. 
Your goal is to update 'CurrentKnowledge' based on the conversation, specifically focusing on the relationship between the AI's last question and the User's response.

STRICT EXTRACTION RULES:
1.  RELEVANCE MATCHING (CRITICAL):
    - Identify which field from <AllowedKeys> the AI's last question was targeting.
    - If the user says "No", "None", "Don't know" (ไม่มี, ไม่รู้, ไม่แน่ใจ), ONLY set that specific targeted field to "None" or "Unknown".
    - DO NOT change any other "__MISSING__" fields to "None" if the user's negative response was not directed at them.

2.  CONTEXT AWARENESS:
    - If the user provides a general "No" (e.g., AI: "Do you have any other symptoms?" User: "No"), only update the field related to 'associated_symptoms'.
    - If the user's reply is completely unrelated to a field, keep that field as "__MISSING__".

3.  DEDUPLICATION & PERSISTENCE:
    - If a field in <CurrentKnowledge> already has a value (other than "__MISSING__"), do not overwrite it unless the user provides a direct update or correction.
    - Fields not mentioned in the current turn or history must remain "__MISSING__".

4.  NO HALLUCINATION:
    - Use ONLY the keys provided in the <AllowedKeys>.
    - Use the exact string "__MISSING__" for any data not yet provided.

<ChatHistory>
{chat_history}
</ChatHistory>

<AllowedKeys>
[{keys_string}]
</AllowedKeys>

<CurrentKnowledge>
{current_data}
</CurrentKnowledge>

<OutputSchema>
{format_instructions}
</OutputSchema>
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
                "format_instructions": parser.get_format_instructions(),
                "keys_string": keys_string
            })
            return res
        except Exception as e:
            print(f"Extraction Error: {e}")
            return {}

    def _format_patient_info(self, info):
        lines = []
        for k, v in info.items():
            if v and v not in ["", "__MISSING__"]:
                lines.append(f"- {k}: {v}")
        return "\n".join(lines)
