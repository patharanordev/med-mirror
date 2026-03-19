import os
from langfuse import get_client
from langfuse.openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LangfuseClient:
    def __init__(self):
        self.langfuse = None
        self.client = None
        self.init()

    def init(self):
        try:
            # Initialize Langfuse client
            self.langfuse = get_client()

            # Verify connection
            if self.langfuse.auth_check():
                print("Langfuse client is authenticated and ready!")
                self.client = OpenAI(
                    base_url=os.getenv("LLM_BASE_URL"),
                    api_key=os.getenv("LLM_API_KEY")
                )

            else:
                print("Authentication failed. Please check your credentials and host.")
        except Exception as e:
            print(f"Failed to initialize Langfuse: {e}")

    def flush(self):
        self.langfuse.flush()

    def load_prompt(self, name, prompt_type, prompt_obj, labels=[], config=None):
        try:
            # 1. Attempt to fetch the existing prompt
            return self.langfuse.get_prompt(name)
        except Exception:
            # 2. If it fails (usually a 404), create it
            print(f"Prompt '{name}' not found. Creating new...")
            return self.langfuse.create_prompt(
                name=name,
                type=prompt_type,
                prompt=prompt_obj,
                config=config,
                labels=labels
            )

    def load_dataset(self, name):
        try:
            return self.langfuse.get_dataset(name=name)
        except Exception:
            print(f"Dataset '{name}' not found. Creating new...")
            
            # Explicitly create the dataset container first
            self.langfuse.create_dataset(name=name)
            
            # Now add the initial item to the newly created dataset
            self.langfuse.create_dataset_item(
                dataset_name=name,
                input="ช่วงนี้ขอบตาดำมากทางยาอะไรดี",
                expected_output="""```json
{
  "next_step": "diagnosis",
  "language": "Thai",
  "shopping_intent": true,
  "reasoning": "The user is asking for medication for dark circles under the eyes, indicating a potential medical concern and a desire to purchase a remedy. This suggests a shopping intent related to medicine or skincare products."
}
```""",
                metadata={"model": "gemma3n:e4b"}
            )

            return self.langfuse.get_dataset(name=name)
