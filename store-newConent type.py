from dotenv import load_dotenv
import os
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain.agents import create_agent
from langchain_ollama import OllamaEmbeddings,ChatOllama
from data import COURSE_URI, extract_html_titles, fetch_fragment, fetch_toc
from query_data import fetch_all_symbols
from search import TextSearch
from readjsScore import lmsStatus,loadData
import json
from tqdm import tqdm
from tqdm.contrib.concurrent import process_map
# Load environment variables from .env file
load_dotenv()
GETDATA=False
api_key=os.getenv("API_KEY")
connection=os.getenv("ConnectionString")
collection_name = os.getenv("collection_name")
lmpFileUri=os.getenv("lmpServerFile")
embeddings = OllamaEmbeddings(
    model="mxbai-embed-large:latest",  # Replace with your pulled model
    base_url="http://localhost:11434",  # Default Ollama URL
    # Optional: Advanced options
    # show_alternate_urls: False,
    # threads: 4,  # Number of threads for computation
)
model = ChatOllama(
    model="llama3.1:8b",
    temperature=0,
    # other params...
)
vector_store = PGVector(
    embeddings=embeddings,
    collection_name=collection_name,
    connection=connection,
    use_jsonb=True,
)
with open("./course_full.json","r") as file:
    data=json.load(file)    
data=list(filter(lambda x:x["content"]!=None,list( data)))
docs=[]
for i in tqdm(range(len(data))):
    item=data[i]
    content= item["content"][0]
    docs.append(Document(page_content=content,metadata={"id":i,"uri":item['uri']}))
        
    vector_store.add_documents(docs, ids=[doc.metadata["id"] for doc in docs])
    
    docs=[]
    
    