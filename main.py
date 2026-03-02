from dotenv import load_dotenv
import os
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain.agents import create_agent
from langchain_ollama import OllamaEmbeddings,ChatOllama
from data import COURSE_URI, extract_html_titles, fetch_toc
from query_data import fetch_document_reference_symbols
from search import TextSearch
from readjsScore import lmsStatus,loadData
import config
# Load environment variables from .env file
load_dotenv()
GETDATA=False
api_key=os.getenv("API_KEY")
dbPath=os.getenv("dbPath")
collection_name = os.getenv("collection_name")
lmpFileUri=os.getenv("lmpServerFile")

model = ChatOllama(
    model="llama3.1:8b",
    temperature=0,
    # other params...
)


lmpData=loadData(lmpFileUri)
if GETDATA:
 files = set()
 toc_html = fetch_toc(COURSE_URI)
 titles_with_html = []
 uri_content_list = []
 extract_html_titles(toc_html, titles_with_html, files, uri_content_list, COURSE_URI)
 docs = [
     Document(page_content=item["content"], metadata={"id": idx,"uri":item["uri"]})
     for idx, item in enumerate(uri_content_list)
 ]
 print(len(docs))
 config.vector_store.add_documents(docs, ids=[doc.metadata["id"] for doc in docs])
 print("finished")


@dynamic_prompt
def prompt_with_context(request: ModelRequest) -> str:
    """Inject context into state messages."""
    last_query = request.state["messages"][-1].text
    text_searchResult= TextSearch(last_query,4)
    retrieved_docs =config.vector_store.similarity_search(last_query)
    symbols= [fetch_document_reference_symbols(doc.metadata["uri"]) for doc in retrieved_docs]
    docs_content = "\n\n".join(doc.page_content for doc in retrieved_docs)
    vector_uri_contnet = [doc.metadata["uri"] for doc in retrieved_docs]
    
    print(vector_uri_contnet)
    # for doc in text_searchResult:
    #     if doc['uri'] not in vector_uri_contnet:
    #         docs_content+= "\n\n"+doc['content']
    #         print(doc['uri'])
     
    system_message = (
        "Your response should mixed of this content:"
        f"\n\n{docs_content}"
    )
    return system_message

agent = create_agent(model, tools=[], middleware=[prompt_with_context])
query = "What is ai agents?"
for step in agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    stream_mode="values",
):
    step["messages"][-1].pretty_print()