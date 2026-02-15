import os
import sys
import asyncio
from langchain_core.messages import HumanMessage, AIMessage

# Add agent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.workflow.med_gemma_4b.nodes.diagnosis.nodes import AskerNode
from app.services.agent_graph import agent_service
from app.core.models import AgentState

async def repro_extraction():
    print("--- Repro Extraction Loop ---")
    
    llm = agent_service.llm
    asker = AskerNode(llm)
    
    # Simulate state where we asked about duration
    # and user replied "2 years"
    
    print("\n[Scenario] Asked about duration, User answers '2 years'")
    messages = [
        HumanMessage(content="I have a problem with my eyes."),
        AIMessage(content="When did it start?"),
        HumanMessage(content="2 years") # Ambiguous for some models?
    ]
    
    # Current known info (duration is missing)
    patient_info = {} 
    
    print("Extracting...")
    extracted = await asker.extract_info(messages, patient_info)
    print(f"Extracted result: {extracted}")
    
    if extracted and extracted.get("onset_and_duration"):
        print("SUCCESS: Duration extracted.")
    else:
        print("FAIL: Duration NOT extracted.")

    # Try Thai
    print("\n[Scenario Thai] User answers '2 ปีแล้ว'")
    messages_thai = [
        HumanMessage(content="มีปัญหาที่ตา"),
        AIMessage(content="เป็นมานานเท่าไหร่แล้วคะ?"),
        HumanMessage(content="2 ปีแล้ว") 
    ]
    
    print("Extracting Thai...")
    extracted_thai = await asker.extract_info(messages_thai, patient_info)
    print(f"Extracted result Thai: {extracted_thai}")

    if extracted_thai and extracted_thai.get("onset_and_duration"):
        print("SUCCESS: Duration extracted (Thai).")
    else:
        print("FAIL: Duration NOT extracted (Thai).")

    # Test Generation (Language Check)
    print("\n[Scenario Generation] Testing Thai Question Generation")
    # Force Missing 'associated_symptoms'
    missing = ["associated_symptoms"]
    thai_hist = [HumanMessage(content="ปวดหัวมากเลย")]
    
    # We need to simulate that ThinkingNode detected "Thai"
    gen_q = await asker.generate_question(patient_info, missing, "associated_symptoms", thai_hist, language="Thai")
    print(f"Generated Thai Question: {gen_q}")
    
    is_thai_char = any('\u0e00' <= char <= '\u0e7f' for char in gen_q)
    if is_thai_char:
         print("SUCCESS: Generated Question contains Thai characters.")
    else:
         print("FAIL: Generated Question seems to be English.")

    # Test Generation (Chinese Check)
    print("\n[Scenario Generation] Testing Chinese Question Generation")
    chinese_hist = [HumanMessage(content="我头痛")]
    gen_q_cn = await asker.generate_question(patient_info, missing, "associated_symptoms", chinese_hist, language="Chinese")
    print(f"Generated Chinese Question: {gen_q_cn}")
    
    if any('\u4e00' <= char <= '\u9fff' for char in gen_q_cn):
        print("SUCCESS: Generated Question contains Chinese characters.")
    else:
        print("FAIL: Generated Question does not look Chinese.")

if __name__ == "__main__":
    asyncio.run(repro_extraction())
