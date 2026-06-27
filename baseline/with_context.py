import json
import os
import sys
import time
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain.agents import create_agent
from bs4 import BeautifulSoup


# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from html_tools import clean_html
from dotenv import load_dotenv
from search import TextSearch
from model import model
from config import vector_store
load_dotenv()

def generatePrompt(query:str)-> str:
    keywords= model.invoke([{"role": "user", "content": f"Give only the key word of this query not any other texts: {query}"}]).content
    retrieved_docs = vector_store.search(query,search_type='similarity',k=4)
    text_searchResult= TextSearch(keywords,4)
    docs_content = "\n".join(f"[URI: {doc.metadata.get('uri')}\n {clean_html(doc.page_content)}]"  for doc in retrieved_docs)
    vector_uri_contnet = [doc.metadata["uri"] for doc in retrieved_docs]
    for doc in text_searchResult:
        if doc['uri'] not in vector_uri_contnet:
            docs_content+= "\n\n"+clean_html(doc['content'])
    sysprompt= f"""
    You are a question-answering model for students. Please provide answers that are easy for students to understand. Use all material provided in the context.
    I provide the user's status regarding some prerequisites of the topic. If the user does not know some prerequisites, cover them before explaining the question to the user.
    Answer in an academic tone.
        User query:
        {query}
        Your response should mixed of this content:
        {docs_content}
        """
    # print(sysprompt)
    return sysprompt
@dynamic_prompt
def prompt_with_context(request: ModelRequest) -> str:
    last_query = request.state["messages"][-1].text
    return generatePrompt(last_query)
agent = create_agent(model, tools=[], middleware=[prompt_with_context])
questions = json.load(open(os.getenv("questions"), "r"))

output_file = "responses_withcontext.json"
results = []
for question in questions[0]['Headers']:
    # time.sleep(20)
    query = question["Title"]
    response_text = ""
    for step in agent.stream(
                   {
                    "messages": [{"role": "user", "content": query}]
                },stream_mode="values"):
        last_message = step["messages"][-1]
        last_message.pretty_print()
        # Only keep the last message if it's from the assistant (AI)
        if hasattr(last_message, "role") and last_message.role == "assistant" or \
           getattr(last_message, "type", None) == "ai" or \
           hasattr(last_message, "content") and not str(last_message.content).strip().startswith(query):
            response_text=last_message.content
    # response_text=generatePrompt(query)    
    results.append({
            "question": query,
            "response": response_text.strip()
        })

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Responses saved to {output_file}")