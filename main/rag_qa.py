import chromadb
from sentence_transformers import SentenceTransformer
import requests
import json
import re
import os

# 載入所有商品資料以供直接查詢
ALL_ITEMS_PATH = "shopee_processed_results-all.json"
with open(ALL_ITEMS_PATH, "r", encoding="utf-8") as f:
    all_items = json.load(f)

# 初始化 ChromaDB
client = chromadb.PersistentClient(path="chroma_store")
collection = client.get_collection(name="coffee")

# 抓出所有已加入的 documents + metadatas
all_data = collection.get(include=["documents", "metadatas"])

# 只印前 5 筆示範
for i, (doc, meta) in enumerate(zip(all_data["documents"], all_data["metadatas"])):
    print(f"\n--- Item {i} ---")
    print("DOCUMENT (你存的內容):")
    print(doc)
    print("\nMETADATA (你存的欄位):")
    print(meta)
    if i >= 4:
        break

# 載入 embedder
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Ollama API 設定
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:0.5b"  # 請填入你的模型名稱

# 關鍵字提取函式
def extract_keywords(text):
    words = re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]+", text)
    return [w.lower() for w in words if len(w) >= 1]

# 直接根據字串在全部資料做子字串比對
def direct_search(query):
    q = query.lower()
    results = []
    for item in all_items:
        name = (item.get("name") or "").lower()
        desc = (item.get("description") or "").lower()
        if q in name or q in desc:
            results.append({
                "name": item.get("name"),
                "price": item.get("price"),
                "sold_count": item.get("sold_count"),
                "rating": item.get("rating"),
                "description": item.get("description"),
                "link": item.get("link")
            })
    return results

# 先做語義檢索，再補上直接檢索結果
def semantic_search(query, n=20):
    emb = embedder.encode([query])[0]
    resp = collection.query(
        query_embeddings=[emb.tolist()],
        n_results=n,
        include=["metadatas"]
    )
    return [m for m in resp.get("metadatas", [[]])[0] if m]

print("請輸入你的問題（或輸入 exit 離開）：")
while True:
    query = input().strip()
    if query.lower() == "exit":
        break

    # 取得語義檢索與直接檢索結果
    sem_results = semantic_search(query, n=15)
    direct_results = direct_search(query)

    # 合併去重
    seen = set([m['name'] for m in sem_results])
    merged = sem_results + [d for d in direct_results if d['name'] not in seen]

    if not merged:
        print("❌ 完全沒有找到相關資料，請換個問法！")
        continue

    # 列印檢索到的資料
    print("\n==== 📝 取得相關資料 ====")
    for i, m in enumerate(merged, start=1):
        print(f"【{i}】{m['name']} - {m['price']}元 ({m['sold_count']}件已售)")

    # 準備上下文給 LLM
    context = "\n\n".join(
        f"商品名稱：{m['name']}\n價格：{m['price']}元\n描述：{m['description']}"
        for m in merged
    )
    prompt = f"""
你是一位咖啡產品分析專家，請根據以下資料回答用戶的問題。

【資料開始】
{context}
【資料結束】

用戶的問題是：「{query}」

回答要求：
- 僅能根據上述資料作答。
- 若資料中找不到相關資訊，請直接回答「資料中沒有相關資訊」。
- 若有符合的商品，請列出商品名稱與價格，並指出最低價。

請用繁體中文回答。
"""

    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    response = requests.post(OLLAMA_API_URL, json=payload)

    if response.status_code == 200:
        data = response.json()
        print("\n==== 🤖 回答 ====")
        print(data.get("response", "⚠️ 無回應內容"))
    else:
        print(f"⚠️ LLM 呼叫失敗，狀態碼：{response.status_code}")
