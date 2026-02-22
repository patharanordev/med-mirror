
import asyncio
import sys
import os
import uuid
from unittest.mock import MagicMock, AsyncMock

# Add agent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mocking ChatOpenAI before importing agent_service
import langchain_openai
original_chat_openai = langchain_openai.ChatOpenAI

# Create a mock class
class MockChatOpenAI:
    def __init__(self, *args, **kwargs):
        self.responses = []
        self.call_count = 0

    def with_structured_output(self, schema):
        return self

    def with_config(self, config):
        return self

    # Simulate invoke
    async def ainvoke(self, input, config=None):
        self.call_count += 1
        print(f"MockLLM invoked. Count: {self.call_count}")
        
        # Logic for ThinkingNode (First call)
        # ThinkingNode chains: prompt | llm.with_structured_output(ThinkingResult)
        # But wait, we are creating a fresh mock for each node instantiation?
        # agent_graph.py instantiates self.llm = ChatOpenAI(...) once.
        # But here we are patching the CLASS or the INSTANCE?
        # Ideally we patch the instance in agent_service.
        return "Mock Response"

    def __or__(self, other):
        return self

# We need to patch the instantiated agent_service.llm and agent_service.llm_diagnosis
from app.services.agent_graph import agent_service
from app.core.models import DiagnosisResult, ThinkingResult

# Setup Mocks
mock_main_llm = AsyncMock()
mock_diagnosis_llm = AsyncMock()

# 1. Thinking Result Mock
thinking_result = ThinkingResult(
    analysis="Mock Analysis",
    todo=["Check symptoms", "Diagnosis"],
    next_step="diagnosis"
)

# 2. Diagnosis Result (Ask Question)
diagnosis_result_q = DiagnosisResult(
    reasoning="Need more info",
    differential_diagnosis=["Condition A", "Condition B"],
    next_step="ask_question",
    question="Is it itchy?",
    confidence=0.5
)

# 3. Diagnosis Result (Explain)
diagnosis_result_e = DiagnosisResult(
    reasoning="Confirmed Condition A",
    differential_diagnosis=["Condition A"],
    next_step="explain",
    final_diagnosis="Condition A",
    is_critical=False,
    confidence=0.9
)

# Explain Node returns AIMessage
from langchain_core.messages import AIMessage
explain_response = AIMessage(content="It is Condition A. Application cream.")


# We need to replace the llm attributes in agent_service
agent_service.llm = mock_main_llm
agent_service.llm_diagnosis = mock_diagnosis_llm

# We need to mock the chains inside the nodes?
# The nodes use `self.llm`. We replaced it.
# But `with_structured_output` needs to return a runnable that returns the Pydantic object.

# Mocking the runnable chain behavior
class MockChain:
    def __init__(self, return_value):
        self.return_value = return_value
    
    def with_config(self, config):
        return self
    
    async def ainvoke(self, input, config=None):
        return self.return_value

# We need to intervene at Node level or LLM level.
# Replacing the Nodes directly might be easier.

async def mock_thinking_node(state, config):
    print("--- MOCK THINKING NODE ---")
    return {"next_step": "diagnosis"}

async def mock_diagnosis_node(state, config):
    print("--- MOCK DIAGNOSIS NODE ---")
    progress = state.get("diagnosis_progress", [])
    if len(progress) == 0:
        # First pass: Ask Question
        return {
            "next_step": "ask_question",
            "diagnostic_question": "Is it itchy?",
            "differential_diagnosis": ["A", "B"],
            "diagnosis_confidence": 0.5,
            "diagnosis_progress": ["Asked question"]
            # messages handled by InterviewNode
        }
    else:
        # Second pass: Explain
        return {
            "next_step": "explain",
            "diagnosis": "Condition A",
            "is_critical": False,
            "differential_diagnosis": ["A"],
            "diagnosis_confidence": 0.9,
            "diagnosis_progress": progress + ["Diagnosed"]
        }

async def mock_explain_node(state, config):
    print("--- MOCK EXPLAIN NODE ---")
    return {"messages": [AIMessage(content="It is Condition A.")]}

# Swap nodes
agent_service.thinking_node = mock_thinking_node
agent_service.diagnosis_node = mock_diagnosis_node
agent_service.explain_node = mock_explain_node

# Use Real InterviewNode (which uses interrupt)
from app.workflow.med_gemma_4b.nodes.interview_node import InterviewNode
# We need to instantiate it with a mock LLM because __init__ expects one
agent_service.interview_node = InterviewNode(mock_main_llm)

# Rebuild graph with mocked nodes
agent_service.graph = agent_service._build_graph()



from langchain_core.messages import HumanMessage
from langgraph.types import Command

async def main():
    print("Starting MOCKED verification of Diagnosis Workflow...")
    
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"--- Step 1: User Input (Symptom) ---")
    inputs = {
        "messages": [HumanMessage(content="I have a red rash.")],
        "context": "Context"
    }
    
    graph = agent_service.get_graph()
    
    # Run until interrupt
    async for event in graph.astream(inputs, config=config):
        for key, value in event.items():
            print(f"Node: {key}")
            if key == "diagnosis":
                 if "diagnostic_question" in value:
                     print(f"  Question: {value['diagnostic_question']}")
    
    # Check state
    snapshot = await graph.aget_state(config)
    
    if snapshot.tasks and snapshot.tasks[0].interrupts:
        print("Graph is INTERRUPTED (Waiting for input). SUCCESS.")
        
        # 2. Provide Answer
        print(f"\n--- Step 2: Provide Answer (Yes, very itchy) ---")
        resume_command = Command(resume={"interrupt_response": "Yes, very itchy"})
        
        async for event in graph.astream(resume_command, config=config):
            for key, value in event.items():
                print(f"Node: {key}")
                if key == "explain":
                    print(f"  Diagnosis: {value.get('diagnosis')}")
                    print(f"  Explanation: {value.get('messages')[0].content}")
        
        # Check final history
        final_snapshot = await graph.aget_state(config)
        print("\nFinal History:")
        for msg in final_snapshot.values['messages']:
            print(f"- {type(msg).__name__}: {msg.content}")

        print("\nVerification Workflow END.")
    else:
        print(f"Graph did NOT interrupt. Next: {snapshot.next}")

if __name__ == "__main__":
    asyncio.run(main())

