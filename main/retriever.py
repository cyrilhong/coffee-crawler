import pandas as pd
import jieba
import json
import re
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from haystack import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
import requests
import os
from haystack_integrations.document_stores.elasticsearch import ElasticsearchDocumentStore

# 初始化 FastAPI
app = FastAPI()

# 添加 jieba 自定義詞典
jieba.add_word("藝妓")
jieba.add_word("藝伎")
jieba.add_word("瑰夏")
jieba.add_word("Geisha")
jieba.add_word("咖啡")
jieba.add_word("生豆")

# 正規化藝妓相關詞
def normalize_geisha(text):
    if not text:
        return ""
    variants = r"藝妓|藝伎|瑰夏|Geisha|藝技|藝姬|geisha咖啡|藝妓咖啡|Geisha咖啡"
    return re.sub(variants, "藝妓", text, flags=re.IGNORECASE)

# 提取資訊，處理無效 scrape_result
def extract_info(row):
    documents = []
    name = normalize_geisha(row.get("name", ""))
    scrape_result = row.get("scrape_result", {})
    item = scrape_result.get("data", {}).get("data", {}).get("item", {})
    
    scrape_status = scrape_result.get("status", "")
    if scrape_status != "success" and not name:
        print(f"跳過無效產品: link={row.get('link', '無連結')}, status={scrape_status}")
        return None

    description = normalize_geisha(item.get("description", ""))
    price_min = item.get("price_min", 0) / 100000 if item.get("price_min") else 0
    price_max = item.get("price_max", 0) / 100000 if item.get("price_max") else 0
    shop = item.get("shop_detailed", {})
    shop_name = shop.get("name", "")
    shop_rating = shop.get("rating_star", 0)
    item_rating = item.get("item_rating", {}).get("rating_star", 0)
    
    attributes = [normalize_geisha(a.get("value", "")) for a in item.get("attributes", [])]
    tier_variations = [normalize_geisha(v.get("name", "")) for v in item.get("tier_variations", [])]
    categories = [normalize_geisha(c.get("display_name", "")) for c in item.get("categories", [])]
    
    text = (
        f"產品：{name}。描述：{description}。"
        f"價格範圍：{price_min} TWD 至 {price_max} TWD。"
        f"商店：{shop_name}，評分 {shop_rating}。商品評分：{item_rating}。"
        f"屬性：{' '.join(attributes)}。變體：{' '.join(tier_variations)}。分類：{' '.join(categories)}。"
    )
    documents.append({
        "content": " ".join(jieba.cut(text)),
        "meta": {
            "item_id": str(item.get("item_id", "")),
            "link": row.get("link", ""),
            "timestamp": str(row.get("timestamp", "")),
            "source": "main_product"
        }
    })
    
    for model in item.get("models", []):
        model_name = normalize_geisha(model.get("name", ""))
        model_price = model.get("price", 0) / 100000 if model.get("price") else 0
        model_text = f"變體：{model_name}。價格：{model_price} TWD。產品：{name}。"
        documents.append({
            "content": " ".join(jieba.cut(model_text)),
            "meta": {
                "item_id": str(item.get("item_id", "")),
                "model_id": str(model.get("model_id", "")),
                "link": row.get("link", ""),
                "source": "model_variant"
            }
        })
    
    if not item and name:
        text = f"產品：{name}。描述：無詳細描述。價格範圍：未知。商店：未知，評分 0。商品評分：0。"
        documents.append({
            "content": " ".join(jieba.cut(text)),
            "meta": {
                "item_id": "",
                "link": row.get("link", ""),
                "timestamp": str(row.get("timestamp", "")),
                "source": "name_only"
            }
        })
    
    return documents

# 初始化文檔儲存和檢索器（僅在啟動時運行一次）
print("正在載入資料並初始化檢索器...")
try:
    df = pd.read_json("shopee_processed_results-all.json")
except FileNotFoundError:
    print("錯誤：未找到 shopee_processed_results-all.json 檔案")
    exit(1)

documents = []
for _, row in df.iterrows():
    result = extract_info(row)
    if result:
        for doc in result:
            documents.append(Document(content=doc["content"], meta=doc["meta"]))

print(f"總文檔數量: {len(documents)}")

embedder = SentenceTransformersTextEmbedder(model="BAAI/bge-small-zh-v1.5")
embedder.warm_up()
for doc in documents:
    doc.embedding = embedder.run(doc.content)["embedding"]

document_store = InMemoryDocumentStore()
document_store.write_documents(documents)
print(f"寫入文檔數量: {document_store.count_documents()}")

retriever = InMemoryEmbeddingRetriever(document_store=document_store)
print("檢索器初始化完成。")

# Grok 3 API 設置
GROK_API_KEY = os.environ.get("GROK_API_KEY", "xai-uD7Aoq0ZjUpiGWjXHgutARiiXXg4bVShhJOvbG3cWnnsu4PC1qcHE3oVndP2aexL7dgj0mx9ZgbW4NO0")

def call_grok_api(query, retrieved_docs):

    context = "\n".join([doc.content for doc in retrieved_docs])
    prompt = (
        f"使用者查詢: {query}\n"
        f"上下文:\n{context}\n"
        "請以中文回答，結構化回應包含以下部分：\n"
        "- **推薦產品**: 列出產品名稱、處理法、價格、風味描述、供應商（如無風味描述則標示為未知）。\n"
        "- **商業洞察**: 提供對咖啡生豆經銷商的商業建議（如性價比、市場需求、進貨建議）。\n"
        "確保回答簡潔，針對經銷商需求。若無相關資料，說明無匹配結果。"
    )
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "grok-3", "prompt": prompt, "max_tokens": 500, "temperature": 0.7}
    try:
        response = requests.post("https://api.x.ai/v1/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["text"]
    except requests.RequestException as e:
        return f"API 錯誤: {str(e)}"

# 網頁介面
@app.get("/", response_class=HTMLResponse)
async def get_form():
    return """
    <html>
        <head>
            <title>咖啡生豆查詢</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container mt-5">
            <h2 class="mb-4">咖啡生豆查詢系統</h2>
            <form method="post" action="/query" class="mb-3">
                <div class="input-group">
                    <input type="text" name="query" class="form-control" placeholder="輸入查詢 (例如 '平價衣索比亞咖啡' 或 '日曬生豆高評分')">
                    <button type="submit" class="btn btn-primary">搜尋</button>
                </div>
            </form>
        </body>
    </html>
    """

@app.post("/query", response_class=HTMLResponse)
async def process_query(query: str = Form(...)):
    # 嵌入查詢
    query_embedding = embedder.run(query)["embedding"]
    # 檢索文檔
    result = retriever.run(query_embedding=query_embedding, top_k=5)
    retrieved_docs = result["documents"]
    
    # 呼叫 Grok 3 API
    answer = call_grok_api(query, retrieved_docs)
    
    # 顯示結果
    result_html = f"""
    <html>
        <head>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container mt-5">
            <h2>查詢: {query}</h2>
            <h3>Grok 回答:</h3>
            <pre>{answer}</pre>
            <h3>檢索到的文檔:</h3>
            <ul>
                {"".join([f"<li>{doc.content} (得分: {doc.score:.4f}, 連結: <a href='{doc.meta['link']}'>{doc.meta['link']}</a>)</li>" for doc in retrieved_docs])}
            </ul>
            <a href="/" class="btn btn-secondary">返回搜尋</a>
        </body>
    </html>
    """
    return result_html

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)