from dotenv import load_dotenv
import os
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain.agents import create_agent
from langchain_ollama import OllamaEmbeddings,ChatOllama
from data import COURSE_URI, extract_html_titles, fetch_fragment, fetch_toc
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
symbols=[] 
def checkChild(parent):
    for child in parent:
        for key in list(child.keys()):
            c=child[key]
            symbols.extend(c["symbols"])
            if c !=None:
                checkChild(c["children"])
with open("mathhub_tree.json","r") as file:
    data=json.load(file) 

for masterKey in data:
    symbols.extend(masterKey[list(masterKey.keys())[0]]["symbols"])
    checkChild(masterKey[list(masterKey.keys())[0]]["children"])
    # for child in masterKey[list(masterKey.keys())[0]]["children"]:
    #     for key in list(child.keys()):
    #         symbols.extend(child[key]["symbols"])
docs=[]        
symbols= list(set(symbols))
for i in tqdm(range(len(symbols))):
    symbol=symbols[i]
    try:
      content= fetch_fragment(symbol)[2]  
      docs.append(Document(page_content=content,metadata={"id":i,"uri":symbol}))
      vector_store.add_documents(docs, ids=[doc.metadata["id"] for doc in docs])
    except:
        pass
            
    docs=[]
        
