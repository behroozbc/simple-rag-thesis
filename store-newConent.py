from dotenv import load_dotenv
import os
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings,ChatOllama
import json
from tqdm import tqdm
import config
# Load environment variables from .env file
load_dotenv()
GETDATA=False
api_key=os.getenv("API_KEY")
connection=os.getenv("ConnectionString")
collection_name = os.getenv("collection_name")
lmpFileUri=os.getenv("lmpServerFile")

with open("./course_full.json","r") as file:
    data=json.load(file)    
data=list(filter(lambda x:x["content"]!=None,list( data)))
docs=[]
for i in tqdm(range(len(data))):
    item=data[i]
    content= item["content"][0]
    docs.append(Document(page_content=content,metadata={"id":str(i+1),"uri":item['uri']}))
        
    config.vector_store.add_documents(docs, ids=[doc.metadata["id"] for doc in docs])
    
    docs=[]
    
    