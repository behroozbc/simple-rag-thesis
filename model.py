from langchain_ollama import ChatOllama
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
load_dotenv()
if os.getenv("isFauModel"):
 model=ChatOpenAI(
    model=os.getenv("fauModel"),
    api_key=os.getenv("fauKey"),
    base_url="https://hub.nhr.fau.de/api/llmgw/v1"
)
else:
    modelName=os.getenv("modelName")
    model = ChatOllama(
        model=modelName,
        temperature=0,
        # other params...
    )
def main():
    print(model.invoke("Hello how are you?"))
if __name__ == "__main__":
    main()