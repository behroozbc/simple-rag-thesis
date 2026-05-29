from langchain_chroma import Chroma
import os
from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
load_dotenv()
collection_name = os.getenv("collection_name")
dbPath=os.getenv("dbPath")

embeddingModelName=os.getenv("embeddingModelName")
match os.getenv("modelProvider"):
    case 'fau':
        embeddings = OpenAIEmbeddings(base_url="https://hub.nhr.fau.de/api/llmgw/v1",api_key=os.getenv('fauKey'),model=embeddingModelName)
    case 'huggingface':
        embeddings= HuggingFaceEmbeddings(embeddingModelName)
    case 'ollama':
        embeddings = OllamaEmbeddings(
        model=embeddingModelName)
    case _:
        embeddings=None
vector_store = Chroma(
    collection_name=collection_name,
    embedding_function=embeddings,
    persist_directory=dbPath
)