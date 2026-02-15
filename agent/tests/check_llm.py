
import os
from langchain_openai import ChatOpenAI

os.environ["LLM_BASE_URL"] = "http://localhost:11434/v1"
os.environ["LLM_API_KEY"] = "ollama"

llm = ChatOpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
    model="qwen3:4b",
    temperature=0
)

try:
    print("Invoking LLM...")
    response = llm.invoke("hi")
    print(f"Response: {response.content}")
except Exception as e:
    print(f"Error: {e}")
