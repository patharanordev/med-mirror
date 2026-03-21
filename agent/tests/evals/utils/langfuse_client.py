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

    def load_dataset(self, name: str, local_data: list):
        self.langfuse.flush()

        try:
            # Temporary Clean-up: Always delete and recreate to clear dirty items
            try:
                self.langfuse.delete_dataset(name=name)
                logging.info(f"Deleted existing dataset '{name}' for fresh start.")
                self.langfuse.flush()
            except Exception as e:
                logging.debug(f"Dataset '{name}' not found or could not be deleted: {e}")

            self.langfuse.create_dataset(name=name)
            dataset = self.langfuse.get_dataset(name=name)
            logging.info(f"Successfully created fresh dataset '{name}'.")
        except Exception as e:
            logging.error(f"Failed during dataset fresh start '{name}': {e}")
            return None
            
        logging.info(f"Syncing {len(local_data)} items to dataset '{name}'...")
        for data in local_data:
            id = data.get('id')
            input = data.get('input')
            expected_output = data.get('expected_output')
            metadata = data.get('metadata', {})
            status = data.get('status', "ACTIVE")
            if input and expected_output:
                try:
                    # Move id to metadata to avoid the 404 creation error seen in logs
                    item_metadata = metadata.copy()
                    if id:
                        item_metadata['original_id'] = id

                    self.langfuse.create_dataset_item(
                        dataset_name=name,
                        input=input,
                        expected_output=expected_output,
                        metadata=item_metadata,
                        status=status
                    )
                    logging.debug(f"Successfully synced item (input hash: {hash(str(input))})")
                except Exception as item_e:
                    logging.debug(f"Item '{id}' sync skipped or failed (likely already exists): {item_e}")

        # Ensure data is sent to the server before returning
        self.langfuse.flush()

        # Re-fetch to get updated items count
        dataset = self.langfuse.get_dataset(name=name)
        logging.info(f"Dataset '{name}' now has {len(dataset.items)} items.")

        return dataset

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