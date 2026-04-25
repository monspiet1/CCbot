from workflow import agentic_rag

input_state = {"query" : "What is the treatment for Alzheimer"}

from pprint import pprint
for step in agentic_rag.stream(input=input_state):
    for key, value in step.items():
        pprint(f"Finished running {key}: ")
pprint(value["response"])