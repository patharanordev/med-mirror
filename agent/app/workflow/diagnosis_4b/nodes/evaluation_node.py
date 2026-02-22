
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from app.core.models import AgentState, PatientInfo
from langchain_core.output_parsers import JsonOutputParser
from app.workflow.common.nodes.patient_sentiment_checker import PatientSentimentChecker
import json

class EvaluationNode:
    def __init__(self, llm):
        self.llm = llm  # Expected: gemma3n:e4b
        self.valid_keys = list(PatientInfo.__fields__.keys())
        self.patient_sentiment_checker = PatientSentimentChecker(llm)
        
    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- DIAGNOSIS 4B: EVALUATION NODE ---")
        
        # 1. Initialize / Load State
        patient_info_dict = state.get("patient_info") or {}
        prev_missing = state.get("missing_keys", [])
        
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

             # Safety: if LLM sentiment says user gave a negative/non-informative answer
             # but extraction still left the previously-asked keys as __MISSING__,
             # force them to "None" so the loop can break.
             targeted_keys = prev_missing[:2]
             still_missing = [k for k in targeted_keys if patient_info_dict.get(k) in (None, "__MISSING__")]
             if still_missing:
                 is_neg = await self.patient_sentiment_checker.is_negative(
                     last_message.content, targeted_keys
                 )
                 if is_neg:
                     for k in still_missing:
                         print(f"DEBUG: Forcing '{k}' to 'None' (sentiment=negative).")
                         patient_info_dict[k] = "None"
        
        # 2. Recalculate Missing Keys
        current_missing = []
        for k in self.valid_keys:
            val = patient_info_dict.get(k)
            # consider missing if None or empty string or "__MISSING__"
            if val is None or str(val).strip() == "__MISSING__":
                current_missing.append(k)
        
        if len(current_missing) == 0:
            return {
                "patient_info": patient_info_dict,
                "missing_keys": current_missing,
                "context": state.get("context", "")
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

        system_prompt = """<role>Precise Medical Data Extractor</role>
<goal>Update the CurrentKnowledge based on the conversation, focusing on the relationship between the AI's last question and the User's response.</goal>

<rules>
  <rule id="1" name="RELEVANCE MATCHING" priority="CRITICAL">
    - Identify which field(s) from AllowedKeys the AI's last question was targeting. The AI may ask about MULTIPLE fields in a single question.
    - Carefully analyze the User's response to see which of the asked fields they answered.
    - If the user gives a blanket negative answer like "No", "None", "Don't know" (ไม่มี, ไม่รู้, ไม่แน่ใจ), ONLY set the specific targeted field(s) to "None" or "Unknown".
    - If the user answers some fields but not others, extract what they answered and keep the unmet fields as "__MISSING__".
    - DO NOT change any other "__MISSING__" fields to "None" if the user's negative response was not directed at them.
  </rule>

  <rule id="2" name="CONTEXT AWARENESS — MULTI-QUESTION HANDLING">
    - The AI might ask about multiple things at once (e.g., "Do you have a fever, and how long have you had this pain?").
    - The User's reply might contain answers to one, multiple, or all of the asked things. Extract ALL relevant pieces of information and map them to their correct keys.
    - Break down the user's response and map each part to the appropriate AllowedKeys.
    - If the user provides a general "No", apply it to all relevant targeted fields being asked about in the previous turn.
    - If the user's reply is completely unrelated to a field, keep that field as "__MISSING__".
  </rule>

  <rule id="3" name="TEMPORAL REASONING — TIME DEDUCTION">
    - You MUST calculate and deduce time durations if the user gives indirect temporal clues.
    - Example 1: If AI asks "Do you get enough sleep?" and User replies "I work 14 hours a day", calculate: 24h - 14h = 10h remaining. Subtracting prep/commute time implies actual sleep is much less (e.g., ~6 hours). Extract this as: "lifestyle_and_sleep": "Works 14 hrs/day, deduced ~6 hrs sleep max".
    - Example 2: If the user says "Since yesterday morning" and today is afternoon, calculate elapsed time (e.g., "duration": "approx 30 hours").
    - Perform mathematical reasoning on hours/days before updating the fields.
  </rule>

  <rule id="4" name="DEDUPLICATION AND PERSISTENCE">
    - If a field in CurrentKnowledge already has a value (other than "__MISSING__"), do not overwrite it unless the user provides a direct update or correction.
    - Fields not mentioned in the current turn or history must remain "__MISSING__".
  </rule>

  <rule id="5" name="NO HALLUCINATION">
    - Use ONLY the keys provided in AllowedKeys.
    - Use the exact string "__MISSING__" for any data not yet provided.
  </rule>
</rules>

<ChatHistory>
{chat_history}
</ChatHistory>

<AllowedKeys>
[{keys_string}]
</AllowedKeys>

<CurrentKnowledge>
{current_data}
</CurrentKnowledge>

<output_format priority="CRITICAL">
  - Return ONLY a raw JSON object string.
  - DO NOT wrap the JSON in markdown code blocks like ```json ... ```.
  - DO NOT add any conversational text, explanations, or greetings before or after the JSON.
  - If you output anything other than exactly the JSON object, the system will break.
  <schema>{format_instructions}</schema>
</output_format>
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
