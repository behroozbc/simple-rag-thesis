from dotenv import load_dotenv
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import duckdb
from tqdm import tqdm
from config import vector_store
from html_tools import clean_html
from model import model
from query_fetch_data import fetch_document, fetch_document_prerequisites, fetch_document_reference_symbols
from readjsScore import LmpUser, getLmpStatus
from search import TextSearch

def promptFunction(current_user:LmpUser, question:str,K=3):
    """Inject context into state messages."""
    
    symbolsOrignal=list()
    returnedUri=list()
    prerequisitesOriginal=list()
    keywords= model.invoke([{"role": "user", "content": f"Give only the key word of this query not any other texts: {question}"}]).content
    text_searchResult= TextSearch(keywords,K)
    retrieved_docs = vector_store.search(question,search_type='similarity',k=K)
    returnedUri.extend(map(lambda x: x['uri'],text_searchResult))
    returnedUri.extend(map(lambda x: x.metadata['uri'],retrieved_docs))
    for uri in returnedUri:
        symbolsOrignal.extend(fetch_document_reference_symbols(uri))
        prerequisitesOriginal.extend(fetch_document_prerequisites(uri))
    docs_content = "\n".join(
        f"[URI: {doc.metadata.get('uri')}\n {clean_html(raw[2])}]"
        for doc in retrieved_docs
        if (raw := fetch_document(doc.metadata.get('uri'))) is not None
        and len(raw) > 2 and isinstance(raw[2], str)
    )
    vector_uri_contnet = [doc.metadata["uri"] for doc in retrieved_docs]
    for doc in text_searchResult:
        if doc['uri'] not in vector_uri_contnet and isinstance(doc.get('content'), str):
            docs_content+= "\n\n"+clean_html(doc['content'])
    symbolsOrignal=list(map(lambda x: {"uri":x,"status":current_user.lmpStatus(x)},symbolsOrignal) )
    
    prerequisites=[{
        "uri": x,
        "status":  current_user.lmpStatus(x),
        "fregment": clean_html(frag)                    # note: probably typo → should be "fragment"
    }
    for x in prerequisitesOriginal
    if (result := fetch_document(x)) is not None
    and len(result) > 2 and isinstance(result[2], str)
    for frag in [result[2]]  ]
    prerequisitesOriginal=list(map(lambda x: {"uri":x,"status":current_user.lmpStatus(x)},prerequisitesOriginal) )
    lmStatus="\n".join(f"[URI: {stat['uri']}, [{json.dumps(stat["status"])}" for stat in symbolsOrignal)
    prerequisitesStatus="\n".join(f"[URI: {pre['uri']} {json.dumps(pre['status'])} \n {pre["fregment"]}]" for pre in prerequisites)
    system_message = (
        f"""
    You are a question-answering model for students. Please provide answers that are easy for students to understand. Use all material provided in the context.
    I provide the user's status regarding some prerequisites of the topic. If the user does not know some prerequisites, cover them before explaining the question to the user.
    Answer in an academic tone.
        User query:
        {question}
        Your response should mixed of this content:
        {docs_content}
        the symbols have understating level as if the user does not know it please explain to it and if the user know skip it:
        {lmStatus}
        this is prerequisites status and content, if the user does not know it please add the content, if the user know skip it:
        {prerequisitesStatus} 
        """
    )
    return system_message, prerequisitesOriginal,symbolsOrignal,docs_content

def main():
    print("Generate A single prompt")
    question= input("Question: ")
    k_input = input("K (default 3): ")
    k = int(k_input) if k_input.strip() else 3
    lmpFileFullAdress= input('LMP file full address: ')
    lmUser= getLmpStatus(lmpFileFullAdress)
    system_message, prerequisitesOriginal, symbolsOrignal, docs_content = promptFunction(lmUser, question, k)
    
    output = {
        "question": question,
        "system_message": system_message,
        "prerequisites": prerequisitesOriginal,
        "symbols": symbolsOrignal,
        "docs_content": docs_content
    }
    
    output_file = "generated_prompt.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nPrompt saved to {output_file}")
    print(f"\n--- System Message ---\n{system_message}")

if __name__ == "__main__":
    main()
    