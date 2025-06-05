import chromadb
from sentence_transformers import SentenceTransformer
import requests
import json
import re
import os

# 設定可配置的 top_k 值
DEFAULT_TOP_K = int(os.environ.get("RAG_TOP_K", 7))

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
embedder = SentenceTransformer("BAAI/bge-small-zh-v1.5")

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
# 修改 semantic_search 函數以使用 DEFAULT_TOP_K 並包含 document content
def semantic_search(query, n=DEFAULT_TOP_K): # Use DEFAULT_TOP_K as default for n
    emb = embedder.encode([query])[0]
    resp = collection.query(
        query_embeddings=[emb.tolist()],
        n_results=n, # n will take the value of DEFAULT_TOP_K from function signature
        include=["metadatas", "documents"] # Include document content
    )

    processed_results = []
    docs = resp.get("documents", [[]])[0]
    metas = resp.get("metadatas", [[]])[0]
    ids = resp.get("ids", [[]])[0] # Assuming ids are always returned and align

    for i in range(len(ids)):
        doc_content = docs[i] if i < len(docs) else None
        meta_content = metas[i] if i < len(metas) else None
        if doc_content and meta_content:
            processed_results.append({'document_content': doc_content, 'metadata': meta_content})
    return processed_results

# 定義新的 LLM 提示模板
new_prompt_template = '''
你是一位專業的咖啡產品顧問。請根據以下提供的多個「資料片段」來回答用戶的問題。
每個片段可能只包含產品的部分資訊（例如，核心資訊、描述的一部分、單一屬性等）。
你需要綜合判斷這些片段，特別注意具有相同「產品ID (`doc_id`)」的片段通常屬於同一個產品。

【資料片段開始】
{context}
【資料片段結束】

用戶的問題是：「{query}」

請依照以下指示作答：
1.  **整合資訊**：如果多個資料片段看起來描述同一個產品（基於內容或元數據中的 `doc_id`），請整合這些資訊來形成對該產品的更完整理解。
2.  **回答問題**：直接回答用戶的問題。
3.  **產品推薦 (若適用)**：如果問題涉及尋找產品，請推薦1至3個最相關的產品。對於每個推薦的產品，請提供：
    *   商品名稱 (可從片段內容或元數據 `name` 獲得)
    *   價格 (可從片段內容或元數據 `price` 獲得)
    *   描述摘要 (從相關片段的 `content` 和元數據中的 `description` 綜合)
    *   商店名稱 (可從片段內容或元數據 `shop_name` 獲得)
    *   (可選) 任何與查詢相關的顯著特點或屬性。
4.  **最低價 (若適用)**：如果查詢要求或上下文中有多個價格，請指出找到的最低價格的商品。
5.  **依據資料**：嚴格根據提供的資料片段作答。不要編造資料以外的資訊。
6.  **無相關資訊**：如果資料片段中確實找不到相關資訊來回答問題，請明確說明「根據提供的資料，找不到相關資訊」。
7.  **語言**：請使用台灣正體中文回答。

請生成您的分析與回答。
'''

print("請輸入你的問題（或輸入 exit 離開）：")
while True:
    query = input().strip()
    if query.lower() == "exit":
        break

    # 取得語義檢索與直接檢索結果
    # semantic_search will now use DEFAULT_TOP_K by default and return new structure
    sem_results = semantic_search(query)
    direct_results = direct_search(query) # direct_results remain old structure

    # 合併去重 - needs adjustment for new sem_results structure
    # For simplicity, direct search results will be added if their names aren't in semantic results' metadata names
    # A more robust deduplication might involve checking doc_id if direct_results also had it
    seen_names_in_semantic = set()
    if sem_results: # Ensure sem_results is not None and not empty
        for res in sem_results:
            if 'metadata' in res and 'name' in res['metadata']:
                 seen_names_in_semantic.add(res['metadata']['name'])

    merged = sem_results + [d for d in direct_results if d.get('name') not in seen_names_in_semantic]


    if not merged:
        print("❌ 完全沒有找到相關資料，請換個問法！")
        continue

    # 列印檢索到的資料 ( angepasst an die neue Struktur )
    print("\n==== 📝 取得相關資料 ====")
    for i, item_data in enumerate(merged, start=1):
        if 'document_content' in item_data: # Semantic result
            metadata = item_data['metadata']
            print(f"【{i}】(語義) {metadata.get('name', 'N/A')} - {metadata.get('price', 'N/A')}元 (區塊類型: {metadata.get('type', 'N/A')})")
            print(f"   內容片段: {item_data['document_content'][:100]}...")
        else: # Direct result
            print(f"【{i}】(直接) {item_data.get('name', 'N/A')} - {item_data.get('price', 'N/A')}元 ({item_data.get('sold_count', 'N/A')}件已售)")


    # 準備上下文給 LLM ( angepasst an die neue Struktur )
    context_items = []
    for i, item_data in enumerate(merged):
        context_item = ""
        if 'document_content' in item_data: # Semantic result
            metadata = item_data['metadata']
            chunk_content = item_data['document_content']
            context_item = (
                f"片段 {i+1} (來源: 語義檢索, "
                f"產品ID: {metadata.get('doc_id', 'N/A')}, "
                f"區塊ID: {metadata.get('chunk_id', 'N/A')}, "
                f"區塊類型: {metadata.get('type', 'N/A')}, "
                f"原始產品名: {metadata.get('name', 'N/A')}, "
                f"原始產品價格: {metadata.get('price', 'N/A')}元):\n"
                f"內容: {chunk_content}"
            )
        else: # Direct result
            chunk_content = (
                f"商品名稱：{item_data.get('name', '')}\n"
                f"價格：{item_data.get('price', '')}元\n"
                f"描述：{item_data.get('description', '')}"
            )
            context_item = (
                f"片段 {i+1} (來源: 直接搜尋, "
                f"產品名: {item_data.get('name', 'N/A')}, "
                f"價格: {item_data.get('price', 'N/A')}元):\n"
                f"內容: {chunk_content}"
            )
        context_items.append(context_item)
    context_string = "\n\n".join(context_items)

    prompt = new_prompt_template.format(context=context_string, query=query)

    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    response = requests.post(OLLAMA_API_URL, json=payload)

    if response.status_code == 200:
        data = response.json()
        print("\n==== 🤖 回答 ====")
        print(data.get("response", "⚠️ 無回應內容"))
    else:
        print(f"⚠️ LLM 呼叫失敗，狀態碼：{response.status_code}")
