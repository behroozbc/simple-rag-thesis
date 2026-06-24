from dotenv import load_dotenv
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import duckdb
from tqdm import tqdm
from config import vector_store
from model import model
from query_fetch_data import fetch_document, fetch_document_prerequisites, fetch_document_reference_symbols
from readjsScore import LmpUser, getLmpsStatus
from search import TextSearch
questions = json.load(open(os.getenv("questions"), "r"))
Lmpsdata = getLmpsStatus('./lmps')
conn = duckdb.connect("db.db")

def promptFunction(current_user:LmpUser, question:str):
    """Inject context into state messages."""
    
    symbolsOrignal=list()
    returnedUri=list()
    prerequisitesOriginal=list()
    keywords= model.invoke([{"role": "user", "content": f"Give only the key word of this query not any other texts: {question}"}]).content
    text_searchResult= TextSearch(keywords,4)
    retrieved_docs = vector_store.search(question,search_type='similarity')
    returnedUri.extend(map(lambda x: x['uri'],text_searchResult))
    returnedUri.extend(map(lambda x: x.metadata['uri'],retrieved_docs))
    for uri in returnedUri:
        symbolsOrignal.extend(fetch_document_reference_symbols(uri))
        prerequisitesOriginal.extend(fetch_document_prerequisites(uri))
    docs_content = "\n".join(f"[URI: {doc.metadata.get('uri')}\n {doc.page_content}]"  for doc in retrieved_docs)
    vector_uri_contnet = [doc.metadata["uri"] for doc in retrieved_docs]
    for doc in text_searchResult:
        if doc['uri'] not in vector_uri_contnet:
            docs_content+= "\n\n"+doc['content']
    symbolsOrignal=list(map(lambda x: {"uri":x,"status":current_user.lmpStatus(x)},symbolsOrignal) )
    
    prerequisites=[{
        "uri": x,
        "status":  current_user.lmpStatus(x),
        "fregment": frag                    # note: probably typo → should be "fragment"
    }
    for x in prerequisitesOriginal
    if (result := fetch_document(x)) is not None
    for frag in [result[2]]  ]
    prerequisitesOriginal=list(map(lambda x: {"uri":x,"status":current_user.lmpStatus(x)},prerequisitesOriginal) )
    lmStatus="\n".join(f"[URI: {stat['uri']}, [{json.dumps(stat["status"])}" for stat in symbolsOrignal)
    prerequisitesStatus="\n".join(f"[URI: {pre['uri']} {json.dumps(pre['status'])} \n {pre["fregment"]}]" for pre in prerequisites)
    system_message = (
        f"""
        Your are an question answer model for students. pls give answer how a student understant. use all material provided in context. 
        I provide to use the user stauts of some pre requiesites of the topic. So If user does not know some pre requisites cover it before explain the question to user.
        Answer on Academic tone.
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

def insert_student_prompt(
    conn: duckdb.DuckDBPyConnection,
    prompt: str,
    question: str,
    user_id: str,
    symbols: list,
    prerequisites: list
) -> str:
    """
    Insert a single record into student_prompts table with new structure
    
    Args:
        conn: DuckDB connection object
        prompt: The prompt text
        question: The question text
        user_id: User identifier
        symbols: List of symbols as JSON array
        prerequisites: List of prerequisites as JSON array
    
    Returns:
        The generated UUID of the inserted record
    """
    
    # Convert lists to JSON strings
    symbols_json = json.dumps(symbols)
    prerequisites_json = json.dumps(prerequisites)
    
    # Insert the record
    return conn.execute("""
        INSERT INTO student_prompts (prompt, question, user_id, symbols, prerequisites, created_at)
        VALUES ( ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, [
        prompt,
        question,
        user_id,
        symbols_json,
        prerequisites_json
    ])



# ====================== PARALLEL PROCESSING ======================

def process_one(student, question):
    """Process one student-question pair (thread-safe)"""
    try:
        prompt, preReq, symbols,_ = promptFunction(student, question['Title'])
        insert_student_prompt(conn, prompt, question['Title'], student.id, symbols, preReq)
        return True
    except Exception as e:
        print(f"Error processing {student.id} - {question['Title']}: {e}")
        return False


# Use threading (adjust max_workers based on your LLM rate limits + CPU)
MAX_WORKERS = 16   # ← tune this (start with 4-8)

tasks = []
for student in Lmpsdata:
    for question in questions[0]['Headers']:
        tasks.append((student, question))

print(f"Total tasks: {len(tasks)}")

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_task = {executor.submit(process_one, student, q): (student.id, q['Title']) 
                      for student, q in tasks}
    
    for future in tqdm(as_completed(future_to_task), total=len(tasks)):
        student_id, q_title = future_to_task[future]
        try:
            future.result()
        except Exception as exc:
            print(f"{student_id} - {q_title} generated an exception: {exc}")

print("✅ All done!")