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
        
        if self.tavily_tool:
            results = await self.tavily_tool.ainvoke(query)
            content = str(results)
        else:
            content = "Search unavailable."
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", settings.get_system_prompt()),
            ("system", "Recommend products based on these search results. keep it concise (max 1-2 sentences with list of products)."),
            ("user", content)
        ])
        
        inputs = {
            "context": state.get("context", "No context"),
        }
        
        chain = (prompt | self.llm).with_config({"run_name": "ShoppingSummarizeChain"})
        response = await chain.ainvoke(inputs, config=config)
        return {"messages": [response]}
