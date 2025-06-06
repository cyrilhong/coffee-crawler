import json
import re
from difflib import get_close_matches

# 標準欄位
STANDARD_FIELDS = [
    "name", "price", "brand", "category", "shop_name", "shop_location", "shop_rating",
    "description", "attributes", "link", "images", "sold_count"
]

# fuzzy match function
def auto_key_mapping(item, standard_fields=STANDARD_FIELDS):
    result = {}
    item_keys = list(item.keys())
    for field in standard_fields:
        # 先精確找
        if field in item:
            result[field] = item[field]
            continue
        # 再fuzzy match（子字串、忽略大小寫、常見變體）
        candidates = [k for k in item_keys if field in k.lower() or k.lower() in field]
        if not candidates:
            # difflib最接近
            matches = get_close_matches(field, item_keys, n=1, cutoff=0.7)
            if matches:
                candidates = matches
        if candidates:
            result[field] = item[candidates[0]]
        else:
            # 最後一層：正則/常見變體
            pat = re.compile(field, re.IGNORECASE)
            for k in item_keys:
                if pat.search(k):
                    result[field] = item[k]
                    break
            else:
                result[field] = ""
    return result

def extract_info(item):
    # 直接用auto_key_mapping產生metadata
    metadata = auto_key_mapping(item)
    # content維持原本格式
    content = "\n".join([f"{k}：{v}" for k, v in metadata.items() if v])
    chunk = {
        "doc_id": str(item.get("itemid") or item.get("item_id") or item.get("link") or ""),
        "type": "core_info",
        "content": content,
        "metadata": metadata
    }
    return [chunk]

def shopee_to_douchao(item):
    # Helper: fuzzy get from dict
    def fuzzy_get(d, keys):
        for k in keys:
            if k in d and d[k] not in [None, ""]:
                return d[k]
        # fuzzy match
        for k in d:
            for key in keys:
                if key in k.lower() or k.lower() in key:
                    if d[k] not in [None, ""]:
                        return d[k]
        # difflib
        for key in keys:
            matches = get_close_matches(key, d.keys(), n=1, cutoff=0.7)
            if matches:
                v = d[matches[0]]
                if v not in [None, ""]:
                    return v
        return None

    # 巢狀抓取
    def nested_get(d, keys, subkeys):
        sub = fuzzy_get(d, keys)
        if isinstance(sub, dict):
            return fuzzy_get(sub, subkeys)
        return None

    # specs mapping
    def extract_specs(item):
        specs = {}
        # product_info/specs/product_description
        for src in [item.get("product_info", {}), item.get("specs", {}), item.get("product_description", {})]:
            if isinstance(src, dict):
                for k, v in src.items():
                    if v not in [None, ""]:
                        specs[k] = v
        return specs if specs else None

    # price_info mapping
    def extract_price_info(item):
        price = fuzzy_get(item, ["price", "價格"])
        if price:
            return {"units": [{"type": "零售價", "weight": "1KG", "price": price}]}
        return None

    # mapping
    return {
        "name": fuzzy_get(item, ["name", "product_name", "商品名稱"]),
        "eng_name": nested_get(item, ["product_info"], ["eng_name", "name"]),
        "country": nested_get(item, ["product_info"], ["country", "origin", "產地"])
            or fuzzy_get(item, ["country", "coffee_origin", "產地"]),
        "region": nested_get(item, ["product_info"], ["region"]) or fuzzy_get(item, ["region", "產區"]),
        "town": nested_get(item, ["product_info"], ["town"]) or fuzzy_get(item, ["town", "莊園"]),
        "category": fuzzy_get(item, ["category", "category_name", "商品分類", "product_category"]),
        "process": nested_get(item, ["product_info"], ["type", "process", "處理法"]) or fuzzy_get(item, ["process", "處理法"]),
        "processing_station": nested_get(item, ["product_info"], ["processing_station"]),
        "specs": extract_specs(item),
        "description": nested_get(item, ["product_info"], ["description", "商品描述"]) or fuzzy_get(item, ["description", "商品描述"]),
        "price_info": extract_price_info(item),
        "season": fuzzy_get(item, ["season", "產季", "year"]),
    }

# 主程式
if __name__ == "__main__":
    with open("data-src/shopee_flatten_results-all.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    with open("output.txt", "w", encoding="utf-8") as f:
        for item in data:
            mapped = shopee_to_douchao(item)
            f.write(json.dumps(mapped, ensure_ascii=False) + "\n")
    print(f"已完成shopee→豆超格式mapping，output.txt每行一個豆超格式JSON。")