import pandas as pd
import jieba
from haystack import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore

# 讀取 JSON
df = pd.read_json("shopee_processed_results-all.json")

# 提取關鍵欄位並清理
def extract_info(row):
    item = row.get("scrape_result", {}).get("data", {}).get("data", {}).get("item", {})
    if not item:
        return None
    name = item.get("title", "")
    price_min = item.get("price_min", 0) / 100000
    price_max = item.get("price_max", 0) / 100000
    shop = item.get("shop_detailed", {})
    shop_name = shop.get("name", "")
    shop_rating = shop.get("rating_star", 0)
    item_rating = item.get("item_rating", {}).get("rating_star", 0)
    text = (
        f"產品：{name}。價格範圍：{price_min} TWD 至 {price_max} TWD。"
        f"商店：{shop_name}，評分 {shop_rating}。商品評分：{item_rating}。"
    )
    return " ".join(jieba.cut(text))

# 應用提取函數並過濾無效資料
df["content"] = df.apply(extract_info, axis=1)
df = df.dropna(subset=["content"])

# 轉為 Haystack Document
documents = [
    Document(
        content=row["content"],
        meta={
            "item_id": str(row.get("scrape_result", {}).get("data", {}).get("data", {}).get("item", {}).get("item_id", "")),
            "link": row.get("link", ""),
            "timestamp": row.get("timestamp", "")
        }
    )
    for _, row in df.iterrows()
]

# Haystack v2 的 InMemoryDocumentStore
document_store = InMemoryDocumentStore()
document_store.write_documents(documents)