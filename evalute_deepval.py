from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase
from deepeval.models import GPTModel
from dotenv import load_dotenv
from deepeval.evaluate import AsyncConfig, ErrorConfig
import os
import duckdb
from tqdm import tqdm
load_dotenv()
conn = duckdb.connect("db.db")
# Initialize your custom OpenAI-compatible model
custom_model = GPTModel(
    model=os.getenv("fauEvalModel"),           # e.g. "llama-3.1-70b", "gpt-4o", "deepseek-chat", etc.
    base_url="https://hub.nhr.fau.de/api/llmgw/v1",  # ← Key parameter
    api_key=os.getenv("fauKey"),       # often "sk-..." or just "EMPTY" / "vllm"
    temperature=0.0,                   # recommended for evaluation
    # generation_kwargs={...}          # any extra params
    
)

# ====================== تنظیمات Metric ======================
metric = AnswerRelevancyMetric(
    threshold=0.7,          
    include_reason=True,
    model=custom_model    
)

# ====================== تست کیس ها از دیتابیس ======================
test_cases = []
query = """
SELECT 
    sp.id, 
    sp.prompt, 
    sp.question, 
    mr.response,
    mr.id as response_id
FROM db.main.student_prompts sp
LEFT JOIN db.main.model_responses mr 
    ON sp.id = mr.student_prompt_id
WHERE mr.response IS NULL 
   OR mr.response NOT LIKE '%MODEL_PROBLEM%'
GROUP BY sp.id, sp.prompt, sp.question, mr.response, mr.id
"""
results = conn.execute(query).fetchall()

for row in results:
    sp_id, prompt, question, response, response_id = row
    if response:
        test_case = LLMTestCase(
            input=question,
            actual_output=response,
            metadata={"response_id":response_id}
        )
        test_cases.append(test_case)

# # روش 2: اجرای دسته‌ای (Batch)
evalResult= evaluate(test_cases, [metric],async_config=AsyncConfig(max_concurrent=5),error_config=ErrorConfig(ignore_errors=True))
# ایجاد جدول نتایج یک‌بار قبل از حلقه
conn.execute("""
    CREATE TABLE IF NOT EXISTS db.main.evaluation_results (
        id uuid DEFAULT uuid(),
        response_id uuid,
        test_name VARCHAR,
        score DOUBLE,
        success BOOLEAN,
        evaluation_model VARCHAR,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# خلاصه نتایج و ذخیره در دیتابیس
results_to_insert = []
for result in tqdm(evalResult.test_results, desc="Processing results"):
    metricResult = result.metrics_data[0]
    response_id = result.metadata.get('response_id')
    
    score = metricResult.score
    success = metricResult.success
    eval_model = metricResult.evaluation_model
    reason = metricResult.reason
    test_name = metricResult.name # The name of the metric/test
    if score!=None:
        results_to_insert.append([response_id, test_name, score, success, eval_model, reason])

# ذخیره دسته‌ای (Batch Insert) برای کارایی بیشتر
if results_to_insert:
    conn.executemany("""
        INSERT INTO db.main.evaluation_results (response_id, test_name, score, success, evaluation_model, reason)
        VALUES (?, ?, ?, ?, ?, ?)
    """, results_to_insert)

print(f"\nSuccessfully stored {len(results_to_insert)} results in db.main.evaluation_results")