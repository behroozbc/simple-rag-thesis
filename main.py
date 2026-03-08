from dotenv import load_dotenv
import os
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain.agents import create_agent
from langchain_ollama import OllamaEmbeddings
from data import COURSE_URI, extract_html_titles, fetch_toc
from query_fetch_data import fetch_document_prerequisites, fetch_document_reference_symbols
from search import TextSearch
from readjsScore import lmsStatus,loadData
import json
from model import model
# Load environment variables from .env file
load_dotenv()
GETDATA=False
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

vector_store = PGVector(
    embeddings=embeddings,
    collection_name=collection_name,
    connection=connection,
    use_jsonb=True,
)
lmpData=loadData(lmpFileUri)

@dynamic_prompt
def prompt_with_context(request: ModelRequest) -> str:
    """Inject context into state messages."""
    last_query = request.state["messages"][-1].text
    symbols=list()
    returnedUri=list()
    prerequisites=list()
    keywords= model.invoke([{"role": "user", "content": f"Give only the key word of this query not any other texts: {last_query}"}]).content
    text_searchResult= TextSearch(keywords,4)
    retrieved_docs = vector_store.similarity_search(last_query)
    returnedUri.extend(map(lambda x: x['uri'],text_searchResult))
    returnedUri.extend(map(lambda x: x.metadata['uri'],retrieved_docs))
    for uri in returnedUri:
        symbols.extend(fetch_document_reference_symbols(uri))
        prerequisites.extend(fetch_document_prerequisites(uri))
    docs_content = "\n\n".join(doc.page_content for doc in retrieved_docs)
    vector_uri_contnet = [doc.metadata["uri"] for doc in retrieved_docs]
    for doc in text_searchResult:
        if doc['uri'] not in vector_uri_contnet:
            docs_content+= "\n\n"+doc['content']
    symbols=list(map(lambda x: {"uri":x,"status":lmsStatus(x,lmpData)},symbols) )
    lmStatus="\n\n".join(stat['uri']+json.dumps(stat["status"]) for stat in symbols)
    system_message = (
        f"""
        User query:
        {last_query}
        Your response should mixed of this content:
        {docs_content}
        the symboles have understanig level as:
        {lmStatus}
        """

    )
    return system_message

agent = create_agent(model, tools=[], middleware=[prompt_with_context])
query = "What is ai agents?"
for step in agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    stream_mode="values",
):
    step["messages"][-1].pretty_print()