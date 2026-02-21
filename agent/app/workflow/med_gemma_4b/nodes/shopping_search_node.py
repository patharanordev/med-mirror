from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from app.core.config import settings
from app.core.models import AgentState

class ShoppingSearchNode:
    def __init__(self, llm, tavily_tool=None):
        self.llm = llm
        self.tavily_tool = tavily_tool

    async def __call__(self, state: AgentState, config: RunnableConfig):
        query = f"products for {state.get('symptoms', 'skin')} on {state.get('body_part', 'body')}"
        
        raw_results = []
        if self.tavily_tool:
            results = await self.tavily_tool.ainvoke(query)
            # Tavily returns a list of dicts with title, url, content, score
            if isinstance(results, list):
                raw_results = results
            content = str(results)
        else:
            content = "Search unavailable."
            
        language = state.get("language", "English")

        summarize_system = """<role>Medical Product Recommender</role>
<language>{language}</language>

<goal>Briefly recommend relevant products based on the search results for the patient's condition.</goal>

<task>
  Read the search results and extract the most relevant product names or resources.
  Present them naturally as a short recommendation — not a list of links, but a helpful suggestion.
</task>

<constraints>
  - CRITICAL: Respond in {language} ONLY. Do NOT add translations in brackets.
  - NEGATIVE: Do NOT greet the user or start with "Okay", "I understand", "Got it", "Sure", or any filler.
  - NEGATIVE: Do NOT say "Thank you" or any closing statement.
  - NEGATIVE: Do NOT repeat or acknowledge the user's previous message.
  - NEGATIVE: Do NOT translate anything inside brackets.
  - No robot talk. Direct and warm tone.
  - Style: Concise, connected, and smart.
  - Keep it to 1-2 sentences max, followed by a short product list if applicable.
</constraints>"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", settings.get_system_prompt()),
            ("system", summarize_system),
            ("user", "{search_results}")
        ])
        
        inputs = {
            "context": state.get("context", "No context"),
            "search_results": content,
            "language": language,
        }
        
        chain = (prompt | self.llm).with_config({"run_name": "ShoppingSummarizeChain"})
        response = await chain.ainvoke(inputs, config=config)
        return {
            "messages": [response],
            "search_results": raw_results,
        }
