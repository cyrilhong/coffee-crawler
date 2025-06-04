import json

def extract_info(item):
    name = item.get("name", "")
    price = item.get("price", "")
    sold_count = item.get("sold_count", "")
    link = item.get("link", "")

    scr = item.get("scrape_result") or {}
    data1 = scr.get("data") or {}
    data2 = data1.get("data") or {}
    item_info = data2.get("item") or {}

    # 商品屬性
    attributes = item_info.get("attributes", [])
    attr_text = ""
    for attr in attributes:
        n = attr.get("name", "")
        v = attr.get("value", "")
        if n and v:
            attr_text += f"{n}：{v}\n"

    # 主要描述
    description = item_info.get("description", "")
    # 補充描述
    if not description:
        description = "\n".join(
            [p.get("text", "") for p in data2.get("product_description", {}).get("paragraph_list", []) if p.get("text")]
        )
    # 其他描述
    if not description:
        description = item_info.get("short_description", "")

    shop_location = item_info.get("shop_location", "")
    rating = item_info.get("item_rating", {}).get("rating_star", "")
    brand = item_info.get("brand", "")
    stock = item_info.get("stock", "")
    category = item_info.get("category_name", "")
    ctime = item_info.get("ctime", "")

    # 賣場詳細資訊
    shop_detailed = data2.get("shop_detailed", {}) or {}
    shop_name = shop_detailed.get("name", "")
    shop_id = shop_detailed.get("shopid", "")
    shop_rating = shop_detailed.get("rating_star", "")

    text = (
        f"商品名稱：{name}\n"
        f"價格：{price} 元\n"
        f"已售出：{sold_count} 件\n"
        f"品牌：{brand}\n"
        f"分類：{category}\n"
        f"庫存：{stock}\n"
        f"上架時間：{ctime}\n"
        f"商店位置：{shop_location}\n"
        f"商店名稱：{shop_name}\n"
        f"商店ID：{shop_id}\n"
        f"商店評分：{shop_rating}\n"
        f"商品評分：{rating}\n"
        f"商品連結：{link}\n"
        f"商品屬性：\n{attr_text}"
        f"商品描述：{description}"
    )
    return text

# 讀取 JSON
with open("shopee_processed_results-all.json", "r", encoding="utf-8") as f:
    data = json.load(f)

docs = []
for item in data:
    docs.append(extract_info(item))

# 輸出
with open("output.txt", "w", encoding="utf-8") as f:
    for doc in docs:
        f.write(doc)
        f.write("\n" + "="*80 + "\n")