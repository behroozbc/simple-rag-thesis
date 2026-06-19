from dotenv import load_dotenv
import os
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
import json
from tqdm import tqdm
import config
# Load environment variables from .env file
load_dotenv()
def clean_text(text: str) -> str:
    text = text.replace('\x00', '')           # remove null bytes
    text = ' '.join(text.split())             # normalize whitespace
    text = text.strip()
    if len(text) < 20:                        # skip very short chunks
        return ""
    return text
GETDATA=False
api_key=os.getenv("API_KEY")
connection=os.getenv("ConnectionString")
collection_name = os.getenv("collection_name")
lmpFileUri=os.getenv("lmpServerFile")

with open("./course_full.json","r") as file:
    data=json.load(file)    
data=list(filter(lambda x:x["content"]!=None,list( data)))
batch_size = 5000
docs = []                         # لیست نهایی اسناد

# حلقهٔ خارجی: پیمایش batch‑ها
for start in tqdm(range(0, len(data), batch_size), desc="Batches"):
    end = min(start + batch_size, len(data))   # اطمینان از خروجی صحیح در آخرین batch
    batch = data[start:end]                    # یک batch از 0 تا 5000 آیتم
    
    # حلقهٔ داخلی: پردازش هر آیتم داخل batch
    for i, item in enumerate(batch, start=start):
        # فرض می‌کنیم `item["content"]` لیستی است و می‌خواهیم اولین مقدارش
        content = item["content"][0]
        if content:
        # ساختن Document و افزودن به لیست نهایی
            docs.append(
            Document(
                page_content=clean_text(content),
                metadata={"id": str(i + 1), "uri": item["uri"]}   # i+1 تا شماره‌گذاری کلی حفظ شود
            )
        )

    config.vector_store.add_documents(docs, ids=[doc.metadata["id"] for doc in docs])
    
    docs=[]
