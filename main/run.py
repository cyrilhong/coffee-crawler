from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from haystack_integrations.document_stores.elasticsearch import ElasticsearchDocumentStore
from haystack.nodes import BM25Retriever
import requests
import os

app = FastAPI()

# Haystack 設置
document_store = ElasticsearchDocumentStore(host="localhost", index="geisha_beans")
retriever = BM25Retriever(document_store=document_store)

# Grok 3 API 設置
GROK_API_KEY = os.environ.get("GROK_API_KEY", "xai-uD7Aoq0ZjUpiGWjXHgutARiiXXg4bVShhJOvbG3cWnnsu4PC1qcHE3oVndP2aexL7dgj0mx9ZgbW4NO0")

def call_grok_api(query, retrieved_docs):
    context = "\n".join([doc.content for doc in retrieved_docs])
    prompt = f"User query: {query}\nContext:\n{context}\nAnswer in a structured format with product name, processing method, price, flavor notes, and supplier."
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "grok-3", "prompt": prompt, "max_tokens": 500, "temperature": 0.7}
    response = requests.post("https://api.x.ai/v1/completions", headers=headers, json=payload)
    return response.json()["choices"][0]["text"] if response.status_code == 200 else "API Error"

# 網頁介面
@app.get("/", response_class=HTMLResponse)
async def get_form():
    return """
    <html>
        <head>
            <title>Geisha Bean Query</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container mt-5">
            <h2 class="mb-4">Geisha Coffee Bean Search</h2>
            <form method="post" action="/query" class="mb-3">
                <div class="input-group">
                    <input type="text" name="query" class="form-control" placeholder="Enter your query (e.g., '馬拉威藝妓平價')">
                    <button type="submit" class="btn btn-primary">Search</button>
                </div>
            </form>
        </body>
    </html>
    """

# 處理查詢
@app.post("/query", response_class=HTMLResponse)
async def process_query(query: str = Form(...)):
    retrieved_docs = retriever.retrieve(query=query, top_k=5)
    answer = call_grok_api(query, retrieved_docs)
    result_html = f"""
    <html>
        <head><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
        <body class="container mt-5">
            <h2>Query: {query}</h2>
            <h3>Answer:</h3>
            <pre>{answer}</pre>
            <h3>Retrieved Documents:</h3>
            <ul>
                {"".join([f"<li>{doc.content}</li>" for doc in retrieved_docs])}
            </ul>
            <a href="/" class="btn btn-secondary">Back to Search</a>
        </body>
    </html>
    """
    return result_html

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)