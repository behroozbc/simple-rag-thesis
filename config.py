from langchain_chroma import Chroma
import os
from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings
load_dotenv()
collection_name = os.getenv("collection_name")
dbPath=os.getenv("dbPath")
embeddingModelName=os.getenv("embeddingModelName")
embeddings = OllamaEmbeddings(
    model=embeddingModelName,  # Replace with your pulled model
    base_url="http://localhost:11434",  # Default Ollama URL
    # Optional: Advanced options
    # show_alternate_urls: False,
    # threads: 4,  # Number of threads for computation
)
vector_store = Chroma(
    collection_name=collection_name,
    embedding_function=embeddings,
    persist_directory=dbPath
)