import chromadb
from sentence_transformers import SentenceTransformer
import json
import os

# 一開始就 PersistentClient
client = chromadb.PersistentClient(path="chroma_store")

# 確保 collection 存到磁碟
try:
    collection = client.get_collection(name="coffee")
except:
    collection = client.create_collection(name="coffee")

# 載入 SentenceTransformer
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# 讀取 output.txt，組成要做向量化的「documents」
documents = []
with open("output.txt", "r", encoding="utf-8") as f:
    current_doc = ""
    for line in f:
        if line.strip() == "=" * 80:
            if current_doc.strip():
                documents.append(current_doc.strip())
                current_doc = ""
        else:
            current_doc += line
    if current_doc.strip():
        documents.append(current_doc.strip())

# 做 embedding
embeddings = embedder.encode(documents)

# 讀取完整商品資料 JSON
with open("shopee_processed_results-all.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 丟進 ChromaDB
for idx, item in enumerate(data):
    # 構造要存入的 document，同時確保所有欄位不會是 None
    document = (
        f"商品名稱：{item.get('name','')}\n"
        f"價格：{item.get('price','')}元\n"
        f"描述：{item.get('description','')}\n"
        f"已售出：{item.get('sold_count','')}件\n"
        f"評分：{item.get('rating','')}分\n"
    )

    # metadata 只保留基本資訊，且轉成原生型別
    metadata = {
        "name": item.get("name", ""),
        "price": float(item.get("price", 0)),
        "sold_count": int(item.get("sold_count", 0)),
        "rating": float(item.get("rating", 0)),
        "description": item.get("description", ""),
        "link": item.get("link", ""),
    }

    collection.add(
        documents=[document],
        metadatas=[metadata],
        embeddings=[embeddings[idx].tolist()],
        ids=[str(idx)]
    )

print("✅ 成功建立向量資料庫！")