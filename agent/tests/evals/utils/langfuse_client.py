from importlib.metadata import metadata
import os, logging
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
                logging.info("Langfuse client is authenticated and ready!")
                self.client = OpenAI(
                    base_url=os.getenv("LLM_BASE_URL"),
                    api_key=os.getenv("LLM_API_KEY")
                )

            else:
                logging.warning("Authentication failed. Please check your credentials and host.")
        except Exception as e:
            logging.error(f"Failed to initialize Langfuse: {e}")

    def flush(self):
        self.langfuse.flush()

    def load_dataset(self, name, local_data:list=[]):
        try:
            return self.langfuse.get_dataset(name=name)
        except Exception as e:
            # Print the ACTUAL error to see what's really failing
            logging.warning(f"Failed to get dataset '{name}'. Reason: {e}")
            logging.info(f"Dataset '{name}' not found. Creating new...")
            
            # Explicitly create the dataset container first
            self.langfuse.create_dataset(name=name)
            
            for data in local_data:
                id = data.get('id')
                input = data.get('input')
                expected_output = data.get('expected_output')
                metadata = data.get('metadata', {})
                status = data.get('status', "ACTIVE")
                if input and expected_output:
                    self.langfuse.create_dataset_item(
                        id=id,
                        dataset_name=name,
                        input=input,
                        expected_output=expected_output,
                        metadata=metadata,
                        status=status
                    )

            # Ensure data is sent to the server before returning
            self.langfuse.flush()

            return self.langfuse.get_dataset(name=name)

    def load_prompt(self, name, prompt_type:str='chat', prompt:str|list=[], labels:list=[]):
        try:
            return self.langfuse.get_prompt(name=name)
        except Exception as e:
            # Print the ACTUAL error to see what's really failing
            logging.warning(f"Failed to get prompt '{name}'. Reason: {e}")

            if prompt != '' or len(prompt) > 0:
                logging.info(f"Prompt '{name}' not found. Creating new...")
                
                # Explicitly create the dataset container first
                self.langfuse.create_prompt(name=name, type=prompt_type, prompt=prompt, labels=labels)

                # Ensure data is sent to the server before returning
                self.langfuse.flush()

                return self.langfuse.get_prompt(name=name)

            return []