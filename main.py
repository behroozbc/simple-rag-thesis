from dotenv import load_dotenv
import os
from langchain_core.documents import Document
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain.agents import create_agent
from data import COURSE_URI, extract_html_titles, fetch_toc
from query_fetch_data import fetch_document, fetch_document_prerequisites, fetch_document_reference_symbols
from search import TextSearch
from readjsScore import getLmpsStatus, lmpStatus
import json
from model import model
from config import vector_store
# Load environment variables from .env file
load_dotenv()
GETDATA=False
connection=os.getenv("ConnectionString")
collection_name = os.getenv("collection_name")
lmpFileUri=os.getenv("lmpServerFile")
questions = json.load(open(os.getenv("questions"), "r"))
# lmpData=loadData(lmpFileUri)
Lmpsdata= getLmpsStatus('./lmps')
@dynamic_prompt
def prompt_with_context(request: ModelRequest) -> str:
    """Inject context into state messages."""
    last_query = request.state["messages"][-1].text
    symbols=list()
    returnedUri=list()
    prerequisites=list()
    keywords= model.invoke([{"role": "user", "content": f"Give only the key word of this query not any other texts: {last_query}"}]).content
    text_searchResult= TextSearch(keywords,4)
    retrieved_docs = vector_store.search(last_query,search_type='similarity')
    returnedUri.extend(map(lambda x: x['uri'],text_searchResult))
    returnedUri.extend(map(lambda x: x.metadata['uri'],retrieved_docs))
    for uri in returnedUri:
        symbols.extend(fetch_document_reference_symbols(uri))
        prerequisites.extend(fetch_document_prerequisites(uri))
    docs_content = "\n".join(f"[URI: {doc.metadata.get('uri')}\n {doc.page_content}]"  for doc in retrieved_docs)
    vector_uri_contnet = [doc.metadata["uri"] for doc in retrieved_docs]
    for doc in text_searchResult:
        if doc['uri'] not in vector_uri_contnet:
            docs_content+= "\n\n"+doc['content']
    symbols=list(map(lambda x: {"uri":x,"status":lmpStatus(x,lmpData)},symbols) )
    prerequisites=[{
        "uri": x,
        "status": lmpStatus(x, lmpData),
        "fregment": frag                    # note: probably typo → should be "fragment"
    }
    for x in prerequisites
    if (result := fetch_document(x)) is not None
    for frag in [result[2]]  ]
    lmStatus="\n".join(f"[URI: {stat['uri']}, [{json.dumps(stat["status"])}" for stat in symbols)
    prerequisitesStatus="\n".join(f"[URI: {pre['uri']} {json.dumps(pre['status'])} \n {pre["fregment"]}]" for pre in prerequisites)
    system_message = (
        f"""
        Your are an question answer model for students. pls give answer how a student understant. use all material provided in context. 
        I provide to use the user stauts of some pre requiesites of the topic. So If user does not know some pre requisites cover it before explain the question to user.
        Answer on Academic tone.
        User query:
        {last_query}
        Your response should mixed of this content:
        {docs_content}
        the symbols have understating level as if the user does not know it please explain to it and if the user know skip it:
        {lmStatus}
        this is prerequisites status and content, if the user does not know it please add the content, if the user know skip it:
        {prerequisitesStatus} 
        """
    )
    return system_message
agent = create_agent(model, tools=[], middleware=[prompt_with_context])
for question in questions[0]['Headers']:
    for lp in Lmpsdata:
        # try:
            lmpData=lp
            query = question["Title"]
            for step in agent.stream(
                {"messages": [{"role": "user", "content": query}]},
            stream_mode="values",):
                step["messages"][-1].pretty_print()
        # except:
        #     print("MODELPROBLEM")


