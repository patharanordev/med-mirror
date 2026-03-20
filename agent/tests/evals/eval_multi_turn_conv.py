# Ref. https://langfuse.com/guides/cookbook/example_evaluating_multi_turn_conversations
from langfuse import observe, Evaluation
from .evals.utils.langfuse_client import LangfuseClient
from .evals.datasets.thinking import local_data
from prompts.thinking import system_message
from models.graph_states.thinking_result_simple import ThinkingResultSimple
from langchain_core.output_parsers import JsonOutputParser

class DiagnosisChat:
    def __init__(self, interview_model="gemma3n:e4b", diagnosis_model="medgemma-1.5:4b"):
        
        self.conversation_history = []
        self.interview_model = interview_model
        self.diagnosis_model = diagnosis_model
        self.lfc = LangfuseClient()
        self.parser = JsonOutputParser(pydantic_object=ThinkingResultSimple)
        
        if self.lfc.langfuse is not None:
            self.client = self.lfc.client
            # self.dataset = self.lfc.load_dataset(
            #     name="med-mirror/darkcircle", 
            # )
            
            def my_task(*, item, **kwargs):
                question = item["input"]
                response = self.client.chat.completions.create(
                    model=self.interview_model,
                    messages=[
                        { 
                            "role": "system", 
                            "content": system_message.format(
                                context="No context", 
                                format_instructions=self.parser.get_format_instructions()
                            )
                        },
                        { "role": "user", "content": question }
                    ],
                    temperature=0,
                    max_tokens=2048
                )
            
                return response.choices[0].message.content

            # Define evaluation functions
            def accuracy_evaluator(*, input, output, expected_output, metadata, **kwargs):
                print(f'output: {output}')
                print(f'expected_output: {expected_output}')
                if expected_output and expected_output.lower() in output.lower():
                    return Evaluation(name="accuracy", value=1.0, comment="Correct answer found")
 
                return Evaluation(name="accuracy", value=0.0, comment="Incorrect answer")
 
            def length_evaluator(*, input, output, **kwargs):
                return Evaluation(name="response_length", value=len(output), comment=f"Response has {len(output)} characters")
 
            def average_accuracy(*, item_results, **kwargs):
                """Calculate average accuracy across all items"""
                accuracies = [
                    eval.value for result in item_results
                    for eval in result.evaluations
                    if eval.name == "accuracy"
                ]
            
                if not accuracies:
                    return Evaluation(name="avg_accuracy", value=None)
            
                avg = sum(accuracies) / len(accuracies)
            
                return Evaluation(name="avg_accuracy", value=avg, comment=f"Average accuracy: {avg:.2%}")

            result = self.lfc.langfuse.run_experiment(
                name="med-mirror",
                description="med-mirror",
                data=local_data,
                task=my_task,
                evaluators=[accuracy_evaluator, length_evaluator],
                run_evaluators=[average_accuracy]
            )
            
            # Use format method to display results
            print(result.format())



            self.prompt = self.lfc.load_prompt(
                name="med-mirror", 
                prompt_type="chat", 
                prompt_obj=[
                    { 
                        "role": "system", 
                        "content": system_message
                    }
                ],
                labels=["production"],
            )

    def close(self):
        self.lfc.flush()

    @observe
    def add_message(self, message):
        try:
            if isinstance(message, str):
                messages = {"role": "user", "content": message}
            
            self.conversation_history.append(messages)

            response = self.client.chat.completions.create(
                model=self.interview_model,
                messages=self.conversation_history,
                temperature=0,
                max_tokens=2048
            )

            assistant_message = response.choices[0].message.content
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            return assistant_message

        except Exception as e:
            return f"Error: {str(e)}"

    def show_history(self):
        import json
        print('Conversation history:')
        print(json.dumps(self.conversation_history, indent=2))
        print()

    def clear_history(self):
        self.conversation_history = []
        print('Conversation cleared!')

chat = DiagnosisChat()
chat.add_message("ช่วงนี้ขอบตาดำมากทางยาอะไรดี")
chat.show_history()
chat.clear_history()

chat.close()