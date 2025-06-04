import json

def flatten_products(data):
    result = []

    for country, value in data.items():
        # 處理有多層類別的（如 Ethiopia, Panama, Colombia）
        if isinstance(value, dict):
            for category, items in value.items():
                # World_Champion_Series 這種只有一個 items 陣列
                if isinstance(items, dict) and "items" in items:
                    for item in items["items"]:
                        product = dict(item)
                        product["country"] = country
                        product["category"] = category
                        result.append(product)
                # 其他正常的類別
                elif isinstance(items, list):
                    for item in items:
                        product = dict(item)
                        product["country"] = country
                        product["category"] = category
                        result.append(product)
        # 處理只有一層的（如 Kenya, Rwanda, Costa_Rica, Nicaragua, Honduras, Bolivia, Peru）
        elif isinstance(value, list):
            for item in value:
                product = dict(item)
                product["country"] = country
                product["category"] = None  # 沒有細分類
                result.append(product)
    return result

# 讀取原始 JSON
with open('2025-05.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 轉換
flat_products = flatten_products(data)

# 輸出新 JSON
with open('2025-05-flat.json', 'w', encoding='utf-8') as f:
    json.dump(flat_products, f, ensure_ascii=False, indent=2)

print(f"已輸出 {len(flat_products)} 筆商品到 2025-05-flat.json")