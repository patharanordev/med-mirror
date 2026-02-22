from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from app.workflow.med_gemma_4b.nodes.shopping_search_node import ShoppingSearchNode
import pytest

@pytest.mark.asyncio
async def test_agent_struct_output():
    try:
        llm = ChatOpenAI(
            base_url="http://localhost:11434/v1",
            model="gemma3n:e4b", 
            api_key="",
            temperature=0)
        node = ShoppingSearchNode(llm)
        state = {
            'messages': [HumanMessage(content='My skin has red patches.')],
            'explanation': 'The patient likely has mild eczema causing red patches.',
            'language': 'English'
        }
        print("Invoking node...")
        res = await node(state, {})
        print("---- RESULTS ----")
        print(res.get('messages', [])[0].content)
        print("Search Results (JSON output):")
        
        assert res.get('search_results') is not None, "Search results are None"
    except Exception as e:
        pytest.fail(f"Test failed with exception: {e}")

