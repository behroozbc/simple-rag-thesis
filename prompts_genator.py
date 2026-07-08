from dotenv import load_dotenv
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import duckdb
from tqdm import tqdm
from config import vector_store
from html_tools import clean_html
from model import model
from prompt_genator import promptFunction
from query_fetch_data import fetch_document, fetch_document_prerequisites, fetch_document_reference_symbols
from readjsScore import LmpUser, getLmpsStatus
from search import TextSearch
questions = json.load(open(os.getenv("questions"), "r"))
Lmpsdata = getLmpsStatus('./lmps')
conn = duckdb.connect("db.db")
K=3


def insert_student_prompt(
    conn: duckdb.DuckDBPyConnection,
    prompt: str,
    docs_content:str,
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
        INSERT INTO student_prompts (prompt,docs_content,K, question, user_id, symbols, prerequisites, created_at)
        VALUES ( ?,?, ?,?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, [
        prompt,
        docs_content,
        K,
        question,
        user_id,
        symbols_json,
        prerequisites_json
    ])



# ====================== PARALLEL PROCESSING ======================

def process_one(student, question):
    """Process one student-question pair (thread-safe)"""
    try:
        prompt, preReq, symbols,docs_content = promptFunction(student, question['Title'],K=K)
        insert_student_prompt(conn, prompt, docs_content,question['Title'], student.id, symbols, preReq)
        return True
    except Exception as e:
        print(f"Error processing {student.id} - {question['Title']}: {e}")
        return False


# Use threading (adjust max_workers based on your LLM rate limits + CPU)
MAX_WORKERS = 18   # ← tune this (start with 4-8)

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