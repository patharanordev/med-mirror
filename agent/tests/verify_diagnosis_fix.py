import asyncio
from app.workflow.diagnosis_4b.nodes.definite_diagnosis_node import DefiniteDiagnosisNode
from langchain_core.messages import AIMessage

class MockLLM:
    def __init__(self, faulty_content):
        self.faulty_content = faulty_content

    async def ainvoke(self, inputs, config=None):
        return AIMessage(content=self.faulty_content)

async def test_parsing_error():
    print("Test 1: Empty String")
    node = DefiniteDiagnosisNode(MockLLM(""))
    res = await node({"messages": [], "context": "test"}, None)
    print(f"Result: {res['diagnosis']}")
    assert res["diagnosis"] == "Unspecified Condition (Parsing Error)"
    assert res["next_step"] == "explain"

    print("\nTest 2: Garbage Text")
    node = DefiniteDiagnosisNode(MockLLM("Garbage content not valid JSON."))
    res = await node({"messages": [], "context": "test"}, None)
    # The new logic uses raw content as thought, and defaults diagnosis
    print(f"Thought: {res['diagnosis_thought_process']}")
    print(f"Result: {res['diagnosis']}")
    assert res["diagnosis"] == "Condition requiring assessment" # Default fallback
    assert res["next_step"] == "explain"

    print("\nTest 3: Valid JSON")
    valid_json = '{"final_diagnosis": "Acne", "confidence": 0.9, "is_critical": false, "next_step": "explain", "differential_diagnosis": []}'
    node = DefiniteDiagnosisNode(MockLLM(valid_json))
    res = await node({"messages": [], "context": "test"}, None)
    print(f"Result: {res['diagnosis']}")
    assert res["diagnosis"] == "Acne"

if __name__ == "__main__":
    asyncio.run(test_parsing_error())
