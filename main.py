import time
from dotenv import load_dotenv
import os
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain.agents import create_agent
from langchain_ollama import OllamaEmbeddings,ChatOllama
from data import COURSE_URI, extract_html_titles, fetch_toc
# Load environment variables from .env file
load_dotenv()
GETDATA=False
api_key=os.getenv("API_KEY")
connection=os.getenv("ConnectionString")
collection_name = os.getenv("collection_name")
# embeddings = RateLimitedEmbeddings(model="models/gemini-embedding-001",google_api_key=api_key)
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
print(connection)
vector_store = PGVector(
    embeddings=embeddings,
    collection_name=collection_name,
    connection=connection,
    use_jsonb=True,
)

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
 vector_store.add_documents(docs, ids=[doc.metadata["id"] for doc in docs])
 print("finished")


@dynamic_prompt
def prompt_with_context(request: ModelRequest) -> str:
    """Inject context into state messages."""
    last_query = request.state["messages"][-1].text
    retrieved_docs = vector_store.similarity_search(last_query)

    docs_content = "\n\n".join(doc.page_content for doc in retrieved_docs)
    print(docs_content)
    system_message = (
        "You are a helpful assistant. Use the following context in your response:"
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