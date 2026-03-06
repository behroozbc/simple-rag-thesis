from langchain_ollama import ChatOllama
from dotenv import load_dotenv
import os
load_dotenv()
modelName=os.getenv("modelName")
model = ChatOllama(
    model=modelName,
    temperature=0,
    # other params...
)
