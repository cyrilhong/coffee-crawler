import json
import pandas as pd
from datetime import datetime
from apify_client import ApifyClient

print("開始爬取蝦皮台灣站點咖啡豆資料...")

# 設置 Apify Client
API_TOKEN = "apify_api_cioOOn10lAyeCFPVowhX1AbCP54ybG1JVn2N"  # 您的 API Token
client = ApifyClient(API_TOKEN)

# 設置 Actor 的輸入參數
input_config = {
    "requests": [
        {"url": "https://shopee.tw/api/v4/search/search_items?keyword=咖啡生豆", "method": "GET"},
        {"url": "https://shopee.tw/api/v4/search/search_items?keyword=咖啡豆", "method": "GET"},
        {"url": "https://shopee.tw/api/v4/search/search_items?keyword=green coffee bean", "method": "GET"}
    ],
    "proxy": {
        "useApifyProxy": True,
        "apifyProxyGroups": ["RESIDENTIAL"],
        "apifyProxyCountry": "TW"
    },
    "productSearch_enrichUrlQuery_pageSize": 60,
    "productSearch_crawlNextPages": True,
    "productSearch_crawlNextPages_maxPages": 3,
    "productSearch_crawlNextPages_maxResults": 180,
    "cookie": "8c5e477e-2b37-4671-a74c-df0542d03492"  # 填入台灣站點的 Request Cookies，例如 "SPC_CDS=xxx;SPC_F=yyy;..."
}

# 運行 Actor 並等待結果
try:
    run = client.actor("marc_plouhinec/shopee-api-scraper").call(run_input=input_config)

    # 收集資料
    data = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        # 除錯：列印原始資料結構
        print("原始資料:", json.dumps(item, ensure_ascii=False, indent=2))

        # 檢查是否為搜尋結果（包含 items 列表）
        items = item.get("responseBody", {}).get("items", [item]) if "items" in item.get("responseBody", {}) else [item.get("item_basic", item)]
        
        for item_data in items:
            data.append({
                "品項": item_data.get("name", item_data.get("title", "未知")),
                "價格": item_data.get("price", item_data.get("price_min", "未知")),
                "賣家": item_data.get("shop_name", item_data.get("shopid", "未知")),
                "地點": item_data.get("shop_location", "未知"),
                "評分": item_data.get("item_rating", {}).get("rating_star", "未知"),
                "已售出": item_data.get("historical_sold", "未知"),
                "庫存": item_data.get("stock", "未知"),
                "收藏數": item_data.get("liked_count", "未知"),
                "連結": item_data.get("url", f"https://shopee.tw/product/{item_data.get('shopid', '')}/{item_data.get('itemid', '')}"),
                "爬取時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    # 檢查是否收集到資料
    if not data:
        raise ValueError("未爬取到任何資料，請檢查 API 響應、Cookies 或搜尋關鍵字")

    # 保存原始 JSON 數據
    with open("shopee_coffee_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 轉換為 DataFrame
    df = pd.DataFrame(data)

    # 處理價格資料
    def clean_price(price):
        if isinstance(price, (int, float)):
            return price / 100000  # 蝦皮 API 價格單位為 10^-5
        elif isinstance(price, str) and price != "未知":
            import re
            match = re.search(r"\d+", price)
            return int(match.group()) if match else "未知"
        return "未知"

    df["價格"] = df["價格"].apply(clean_price)

    # 存為 CSV
    df.to_csv("shopee_coffee_data.csv", index=False, encoding="utf-8-sig")

    print(f"爬取完成，資料已存至 shopee_coffee_data.json 和 shopee_coffee_data.csv")
    print("\n資料預覽：")
    print(df.head())

except Exception as e:
    print(f"爬蟲執行失敗，錯誤訊息：{str(e)}")