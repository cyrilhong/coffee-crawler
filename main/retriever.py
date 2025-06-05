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
# from haystack_integrations.document_stores.elasticsearch import ElasticsearchDocumentStore # Commented out as not used in current InMemory setup

# 設定可配置的 top_k 值
DEFAULT_TOP_K = int(os.environ.get("RAG_TOP_K", 7)) # Same default as rag_qa.py for consistency

# 初始化 FastAPI
app = FastAPI()

# 添加 jieba 自定義詞典
jieba.add_word("藝妓")
jieba.add_word("藝伎")
jieba.add_word("瑰夏")
jieba.add_word("Geisha")
jieba.add_word("咖啡")
jieba.add_word("生豆")
# Add more terms that might be relevant for segmentation or search
jieba.add_word("水洗")
jieba.add_word("日曬")
jieba.add_word("蜜處理")
jieba.add_word("厭氧")
jieba.add_word("半水洗")
jieba.add_word("酒香")
jieba.add_word("花香")
jieba.add_word("果香")


# 正規化藝妓相關詞
def normalize_geisha(text):
    if not text or not isinstance(text, str): # Added type check for safety
        return ""
    variants = r"藝妓|藝伎|瑰夏|Geisha|藝技|藝姬|geisha咖啡|藝妓咖啡|Geisha咖啡"
    return re.sub(variants, "藝妓", text, flags=re.IGNORECASE)

# 提取資訊，處理無效 scrape_result
def extract_info(row):
    product_document_specs = []

    # 1. Initial Data Extraction from `row`
    product_link = row.get("link", "")
    initial_product_name = normalize_geisha(row.get("name", ""))
    scrape_result_data = row.get("scrape_result", {})
    scrape_status = scrape_result_data.get("status", "")
    # Ensure data.data.item path is safely accessed
    item_details_container = scrape_result_data.get("data", {})
    item_details = item_details_container.get("data", {}).get("item", {}) if isinstance(item_details_container, dict) else {}


    # 2. Handle Invalid/Insufficient Data
    if scrape_status != "success" and not initial_product_name:
        # print(f"Skipping invalid product: link={product_link}, status={scrape_status}") # Reduced verbosity
        return None

    product_item_id = str(item_details.get("itemid", item_details.get("item_id", "")))

    if not item_details and initial_product_name: # Name-only case
        name_only_content_text = f"產品：{initial_product_name}。描述：無詳細描述。價格範圍：未知。商店：未知，評分 0。商品評分：0。"
        name_only_content = " ".join(jieba.cut(name_only_content_text))
        name_only_meta = {
            "item_id": "",
            "link": product_link,
            "name": initial_product_name,
            "timestamp": str(row.get("timestamp", "")),
            "source": "name_only",
            "chunk_type": "core_info",
            "price_min": 0.0,
            "price_max": 0.0,
            "shop_name": "未知",
            "shop_rating": 0.0,
            "item_rating": 0.0,
            "categories": "",
            "full_description": "無詳細描述"
        }
        return [{"content": name_only_content, "meta": name_only_meta}]

    # 3. Core Information Extraction (from `item_details`)
    effective_product_name = normalize_geisha(item_details.get("name", initial_product_name))
    if not effective_product_name and initial_product_name:
        effective_product_name = initial_product_name
    elif not effective_product_name and not initial_product_name:
        # print(f"Skipping product with no discernible name: link={product_link}") # Reduced verbosity
        return None


    full_description = normalize_geisha(item_details.get("description", ""))
    min_price = item_details.get("price_min", 0) / 100000 if item_details.get("price_min") else 0.0
    max_price = item_details.get("price_max", 0) / 100000 if item_details.get("price_max") else 0.0
    
    shop_details_container = item_details_container.get("data", {})
    shop_details = shop_details_container.get("shop_detailed", {}) if isinstance(shop_details_container, dict) else {}
    if not shop_details:
        shop_details = item_details.get("shop_detailed", {})

    shop_name_text = shop_details.get("name", "未知")
    shop_rating_value = float(shop_details.get("rating_star", 0.0))
    item_rating_value = float(item_details.get("item_rating", {}).get("rating_star", 0.0))

    product_categories_raw = item_details.get("categories", [])
    product_categories = [normalize_geisha(c.get("display_name", "")) for c in product_categories_raw if isinstance(c, dict) and c.get("display_name")] if product_categories_raw else []
    
    product_attributes_list_raw = item_details.get("attributes", [])
    product_attributes_list = product_attributes_list_raw if product_attributes_list_raw else []

    product_models_raw = item_details.get("models", [])
    product_models = product_models_raw if product_models_raw else []

    # 4. Base Metadata for All Chunks of a Product
    common_metadata = {
        "item_id": product_item_id,
        "link": product_link,
        "name": effective_product_name,
        "price_min": min_price,
        "price_max": max_price,
        "shop_name": shop_name_text,
        "shop_rating": shop_rating_value,
        "item_rating": item_rating_value,
        "categories": " ".join(product_categories),
        "full_description": full_description,
        "timestamp": str(row.get("timestamp", ""))
    }

    # 6. Chunk Type 1: core_info
    core_info_content_text = (
        f"產品：{effective_product_name}。"
        f"價格範圍：{min_price:.2f} TWD 至 {max_price:.2f} TWD。"
        f"商店：{shop_name_text}，評分 {shop_rating_value:.2f}。"
        f"商品評分：{item_rating_value:.2f}。"
        f"分類：{' '.join(product_categories) if product_categories else '無分類'}。"
    )
    core_info_meta = common_metadata.copy()
    core_info_meta.update({"chunk_type": "core_info", "source": "main_product_core"})
    product_document_specs.append({"content": " ".join(jieba.cut(core_info_content_text)), "meta": core_info_meta})

    # 7. Chunk Type 2: description_segment
    if full_description:
        segment_length = 120
        overlap = 30

        if len(full_description) <= segment_length:
            if full_description.strip():
                description_segment_meta = common_metadata.copy()
                description_segment_meta.update({"chunk_type": "description_segment", "source": "main_product_description"})
                product_document_specs.append({"content": " ".join(jieba.cut(full_description)), "meta": description_segment_meta})
        else:
            start_index = 0
            while start_index < len(full_description):
                segment = full_description[start_index : start_index + segment_length]
                if not segment.strip():
                    if start_index + segment_length >= len(full_description):
                        break
                    start_index += (segment_length - overlap)
                    continue

                description_segment_meta = common_metadata.copy()
                description_segment_meta.update({"chunk_type": "description_segment", "source": "main_product_description"})
                product_document_specs.append({"content": " ".join(jieba.cut(segment)), "meta": description_segment_meta})

                if start_index + segment_length >= len(full_description):
                    break
                start_index += (segment_length - overlap)


    # 8. Chunk Type 3: attribute_info
    if isinstance(product_attributes_list, list):
        for attr in product_attributes_list:
            if not isinstance(attr, dict): continue
            attr_name = normalize_geisha(attr.get("name", ""))
            attr_value = normalize_geisha(attr.get("value", ""))
            if attr_name and attr_value:
                attribute_content_text = f"商品屬性：{attr_name} - {attr_value}"
                attribute_meta = common_metadata.copy()
                attribute_meta.update({"chunk_type": "attribute_info", "source": "main_product_attributes"})
                product_document_specs.append({"content": " ".join(jieba.cut(attribute_content_text)), "meta": attribute_meta})

    # 9. Chunk Type 4: model_variant
    if isinstance(product_models, list):
        for model in product_models:
            if not isinstance(model, dict): continue
            model_name_text = normalize_geisha(model.get("name", ""))
            model_price_value = model.get("price", 0) / 100000 if model.get("price") else 0.0

            if not model_name_text:
                continue

            model_content_text = f"變體：{model_name_text}。價格：{model_price_value:.2f} TWD。此為產品 {effective_product_name} 的一個規格選項。"
            model_meta = common_metadata.copy()
            model_meta.update({
                "chunk_type": "model_variant",
                "source": "model_variant",
                "model_id": str(model.get("modelid", model.get("model_id", ""))),
                "model_name": model_name_text,
                "model_price": model_price_value
            })
            model_meta["price_min"] = model_price_value
            model_meta["price_max"] = model_price_value
            product_document_specs.append({"content": " ".join(jieba.cut(model_content_text)), "meta": model_meta})
    
    if not product_document_specs:
        return None

    return product_document_specs


# 初始化文檔儲存和檢索器（僅在啟動時運行一次）
print("正在載入資料並初始化檢索器...")
document_store = InMemoryDocumentStore() # Initialize regardless of data presence
retriever = InMemoryEmbeddingRetriever(document_store=document_store)
embedder = SentenceTransformersTextEmbedder(model="BAAI/bge-small-zh-v1.5") # Initialize embedder early

try:
    df = pd.read_json("../data-src/shopee_flatten_results-all.json") # Path changed to ../data-src/
except FileNotFoundError:
    print("錯誤：未找到 ../data-src/shopee_flatten_results-all.json 檔案。將使用空文檔庫。") # Updated error message
    df = pd.DataFrame()
except Exception as e:
    print(f"讀取 JSON 時發生錯誤: {e}。將使用空文檔庫。")
    df = pd.DataFrame()


all_document_specs = []
if not df.empty:
    for _, row_data in df.iterrows():
        specs = extract_info(row_data)
        if specs:
            all_document_specs.extend(specs)
else:
    print("Warning: DataFrame is empty, no data to process for Haystack.")


documents_for_haystack = []
if all_document_specs:
    for spec in all_document_specs:
        if isinstance(spec.get("meta"), dict) and isinstance(spec.get("content"), str):
            documents_for_haystack.append(Document(content=spec["content"], meta=spec["meta"]))
        else:
            print(f"Warning: Skipping invalid document spec due to type mismatch or missing fields: {spec}")
else:
    print("Warning: No document specifications were generated from the input file.")


print(f"總文檔數量 (Total documents for Haystack): {len(documents_for_haystack)}")

if documents_for_haystack:
    print(f"正在暖機嵌入模型 BAAI/bge-small-zh-v1.5...")
    embedder.warm_up()
    print(f"正在為 {len(documents_for_haystack)} 個文檔嵌入向量...")
    for i, doc in enumerate(documents_for_haystack):
        try:
            if not isinstance(doc.content, str) or not doc.content.strip():
                print(f"Warning: Document {i} has empty or invalid content. Skipping embedding. Meta: {doc.meta}")
                doc.embedding = None
                continue
            doc.embedding = embedder.run(text=doc.content)["embedding"]
        except Exception as e:
            print(f"Error embedding document {i}. Content: '{doc.content[:100]}...'. Error: {e}")
            doc.embedding = None

    documents_for_haystack = [doc for doc in documents_for_haystack if doc.embedding is not None]
    print(f"成功嵌入 {len(documents_for_haystack)} 個文檔。")

    if documents_for_haystack:
        document_store.write_documents(documents_for_haystack)
        print(f"寫入文檔數量 (Documents written to Haystack): {document_store.count_documents()}")
    else:
        print("沒有成功嵌入的文檔可寫入 Haystack DocumentStore。")
else:
    print("沒有文檔可供嵌入或寫入 Haystack DocumentStore。")

print("檢索器初始化完成。")

# Grok 3 API 設置
GROK_API_KEY = os.environ.get("GROK_API_KEY")
if not GROK_API_KEY:
    print("Warning: GROK_API_KEY environment variable not set. Grok API calls will fail.")

def call_grok_api(query, retrieved_docs):
    if not GROK_API_KEY:
        return "API Key for Grok not configured. Cannot fetch insights."

    context_parts = []
    for i, doc in enumerate(retrieved_docs):
        doc_info = (
            f"文檔 {i+1} (產品名稱: {doc.meta.get('name', 'N/A')}, "
            f"項目ID: {doc.meta.get('item_id', 'N/A')}, "
            f"區塊類型: {doc.meta.get('chunk_type', 'N/A')}, "
            f"商店: {doc.meta.get('shop_name', 'N/A')}, "
            f"{'模型ID: ' + doc.meta.get('model_id', 'N/A') + ', ' if doc.meta.get('chunk_type') == 'model_variant' else ''}"
            f"價格: {str(doc.meta.get('price_min', '')) + (' - ' + str(doc.meta.get('price_max', '')) if doc.meta.get('price_min') != doc.meta.get('price_max') else '') + ' TWD' if doc.meta.get('price_min') is not None else '未知'}):\n"
            f"內容片段: {doc.content}"
        )
        context_parts.append(doc_info)
    context = "\n\n".join(context_parts)

    prompt = (
        f"使用者查詢: {query}\n\n"
        f"上下文 (來自相似度搜尋的咖啡產品資料片段 - 請注意這些是『片段』，可能只包含產品的部分資訊，例如核心資訊、描述、單一屬性或一個規格型號。你需要綜合判斷):\n{context}\n\n"
        "任務指南:\n"
        "1. **分析上下文**: 仔細閱讀以上提供的多個文檔片段。每個片段可能描述產品核心資訊、描述、屬性或特定規格(變體)。`item_id` 相同表示它們來自同一個產品頁面。\n"
        "2. **識別與整合產品**: 根據上下文，識別出不同的咖啡產品。對於每個主要產品 (由 `item_id` 區分), 嘗試整合其所有相關片段 (核心、描述、屬性、變體) 的資訊，以形成對該產品的較完整理解。\n"
        "3. **生成推薦**: \n"
        "   - **推薦產品**: 根據使用者查詢的相關性，列出最多3-5個產品。對於每個產品，提供：產品名稱、價格（或價格範圍，利用 `price_min` 和 `price_max`）、關鍵風味/特性（從 `content` 或 `full_description` in `meta` 推斷）、供應商名稱 (`shop_name`)。\n"
        "     如果資訊不完整（例如，缺少風味描述），請明確指出「風味描述待確認」或「價格未提供」。\n"
        "   - **格式**: 使用項目符號或清晰的段落來呈現每個推薦產品。\n"
        "4. **商業洞察**: 根據查詢和檢索到的產品情況，提供1-2條對咖啡生豆經銷商的商業建議（例如，市場趨勢、庫存建議、採購策略、性價比分析等）。\n"
        "5. **語言**: 請務必以台灣正體中文回答。\n"
        "6. **無結果處理**: 如果檢索到的文檔與查詢不相關，或者資訊不足以形成推薦，請說明「根據提供的資料，無法找到匹配的產品或無法提供具體建議」。\n\n"
        "請基於以上指示，生成您的回應。"
    )
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "grok-3", "prompt": prompt, "max_tokens": 1200, "temperature": 0.55}
    try:
        response = requests.post("https://api.x.ai/v1/completions", headers=headers, json=payload)
        response.raise_for_status()
        choice = response.json().get("choices", [{}])[0]
        if not choice: # Handle empty choices list
             print(f"Grok API returned empty choices. Response: {response.json()}")
             return "Grok API 未返回有效選擇。"
        return choice.get("text", "Grok API 回應格式不符或為空。")
    except requests.exceptions.RequestException as e:
        print(f"Grok API request error: {e}")
        return f"呼叫 Grok API 時發生網路或請求錯誤: {e}"
    except json.JSONDecodeError:
        print(f"Grok API response JSON decode error. Response text: {response.text}")
        return "無法解析 Grok API 的回應 (JSON 解碼失敗)。"
    except KeyError: # Handles cases where 'choices' or 'text' might be missing
        print(f"Grok API response unexpected structure. Response JSON: {response.json()}")
        return "Grok API 回應結構異常。"
    except IndexError: # Handles cases where 'choices' list might be empty
        print(f"Grok API response 'choices' list is empty. Response JSON: {response.json()}")
        return "Grok API 回應中 'choices' 列表為空。"


# 網頁介面
@app.get("/", response_class=HTMLResponse)
async def get_form():
    return """
    <html>
        <head>
            <title>咖啡生豆查詢（Haystack - Granular）</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body { font-family: 'Arial', sans-serif; padding-top: 20px; background-color: #f8f9fa; }
                .container { max-width: 800px; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 0 15px rgba(0,0,0,0.1); }
                h2 { color: #343a40; }
                .btn-primary { background-color: #007bff; border-color: #007bff; }
                .alert { white-space: pre-wrap; word-wrap: break-word; }
            </style>
        </head>
        <body class="container mt-5">
            <h2 class="mb-4 text-center">咖啡生豆查詢系統 (Haystack - 細粒度文檔)</h2>
            <form method="post" action="/query" class="mb-3">
                <div class="input-group mb-3">
                    <input type="text" name="query" class="form-control form-control-lg" placeholder="輸入查詢 (例如 '平價衣索比亞藝妓' 或 '日曬高評分')">
                    <button type="submit" class="btn btn-primary btn-lg">搜尋</button>
                </div>
            </form>
            <div id="results" class="mt-4"></div>
        </body>
    </html>
    """

@app.post("/query", response_class=HTMLResponse)
async def process_query(query: str = Form(...)):
    print(f"接收到查詢: {query}")
    query_embedding_result = embedder.run(text=query)
    query_embedding = query_embedding_result["embedding"]
    
    # Use DEFAULT_TOP_K for retrieval
    print(f"使用 top_k={DEFAULT_TOP_K} 進行檢索...")
    retrieval_result = retriever.run(query_embedding=query_embedding, top_k=DEFAULT_TOP_K)
    retrieved_docs = retrieval_result["documents"]
    print(f"檢索到 {len(retrieved_docs)} 個文檔區塊。")

    print("正在呼叫 Grok API...")
    answer = call_grok_api(query, retrieved_docs)
    print("Grok API 回應已接收。")
    
    results_list_html = ""
    if retrieved_docs:
        results_list_html = "<ul class='list-group list-group-flush'>"
        for doc_idx, doc in enumerate(retrieved_docs):
            meta_display = f"產品: {doc.meta.get('name', 'N/A')}, ItemID: {doc.meta.get('item_id', 'N/A')}, Chunk: {doc.meta.get('chunk_type', 'N/A')}"
            if doc.meta.get('chunk_type') == 'model_variant':
                meta_display += f", Model: {doc.meta.get('model_name', 'N/A')}"

            link = doc.meta.get('link', '#')
            results_list_html += (
                f"<li class='list-group-item small p-2'>"
                f"<b>{doc_idx+1}. {doc.meta.get('name', '未知產品')}</b> ({meta_display})<br/>"
                f"<i>內容片段:</i> {doc.content[:200]}... <br/>"
                f"(得分: {doc.score:.4f}, <a href='{link}' target='_blank'>產品連結</a>)"
                f"</li>"
            )
        results_list_html += "</ul>"
    else:
        results_list_html = "<p>無檢索到相關文檔。</p>"

    output_html = f"""
    <html>
        <head>
            <title>查詢結果: {query}</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ font-family: 'Arial', sans-serif; padding-top: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 900px; }}
                .card {{ margin-bottom: 20px; }}
                .card-header {{ background-color: #e9ecef; font-weight: bold; }}
                .card-body pre {{ white-space: pre-wrap; word-wrap: break-word; background-color: #f8f9fa; padding: 15px; border-radius: 4px; font-size: 0.9rem;}}
                .retrieved-docs-container {{ max-height: 450px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px; background-color: #fff;}}
                .small p {{ margin-bottom: 0.5rem; }}
            </style>
        </head>
        <body class="container mt-4">
            <a href="/" class="btn btn-outline-secondary mb-3">&laquo; 返回搜尋頁面</a>

            <div class="card">
                <div class="card-header">
                    查詢: {query}
                </div>
                <div class="card-body">
                    <h5>Grok AI 回應:</h5>
                    <pre>{answer}</pre>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    檢索到的相關文檔區塊 (Top {len(retrieved_docs)}):
                </div>
                <div class="card-body retrieved-docs-container">
                    {results_list_html}
                </div>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=output_html)

if __name__ == "__main__":
    import uvicorn
    if not os.environ.get("GROK_API_KEY"):
       print("CRITICAL: GROK_API_KEY environment variable must be set to run the application.")
    uvicorn.run(app, host="0.0.0.0", port=8000)
