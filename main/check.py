import json
import re

# 正規化藝妓相關詞
def normalize_geisha(text):
    if not text:
        return ""
    variants = r"藝妓|藝伎|瑰夏|Geisha|藝技|藝姬|geisha咖啡|藝妓咖啡|Geisha咖啡"
    return re.sub(variants, "藝妓", text, flags=re.IGNORECASE)

# 檢查單個產品的所有欄位
def check_geisha_in_product(product):
    """檢查產品的所有欄位是否包含『藝妓』，包括頂層 name 和 scrape_result"""
    geisha_fields = {}
    error_msg = None
    
    # 檢查頂層 name 欄位
    name = product.get("name", "")
    normalized_name = normalize_geisha(str(name))
    if "藝妓" in normalized_name:
        geisha_fields["name"] = name
    
    # 檢查 scrape_result 中的 item
    item = product.get("scrape_result", {}).get("data", {}).get("data", {}).get("item", {})
    if not item:
        # 檢查 scrape_result 的狀態
        scrape_status = product.get("scrape_result", {}).get("status", "")
        if scrape_status != "success":
            error_msg = f"scrape_result 非成功狀態: {scrape_status}, link: {product.get('link', '無連結')}"
        elif "message" in product.get("scrape_result", {}).get("data", {}):
            error_msg = f"scrape_result 包含錯誤訊息: {product.get('scrape_result', {}).get('data', {}).get('message', '')}, link: {product.get('link', '無連結')}"
        else:
            error_msg = f"無有效 item 數據，link: {product.get('link', '無連結')}"
    else:
        # 提取所有可能包含文字的欄位
        fields = {
            "title": item.get("title", ""),
            "description": item.get("description", ""),
            "models": [m.get("name", "") for m in item.get("models", [])],
            "attributes": [a.get("value", "") for a in item.get("attributes", [])],
            "tier_variations": [v.get("name", "") for v in item.get("tier_variations", [])],
            "categories": [c.get("display_name", "") for c in item.get("categories", [])],
        }
        
        # 正規化並檢查
        for field_name, field_value in fields.items():
            if isinstance(field_value, list):
                normalized_values = [normalize_geisha(str(v)) for v in field_value]
                if any("藝妓" in v for v in normalized_values):
                    geisha_fields[field_name] = [v for v in field_value if "藝妓" in normalize_geisha(str(v))]
            else:
                normalized_value = normalize_geisha(str(field_value))
                if "藝妓" in normalized_value:
                    geisha_fields[field_name] = field_value
    
    if geisha_fields:
        return True, geisha_fields, error_msg
    return False, None, error_msg

# 檢查資料源
with open("shopee_processed_results-all.json", "r", encoding="utf-8") as f:
    data = json.load(f)

geisha_products = []
invalid_products = []

for p in data:
    contains_geisha, geisha_fields, error_msg = check_geisha_in_product(p)
    if contains_geisha:
        geisha_products.append((p, geisha_fields))
    if error_msg:
        invalid_products.append(error_msg)

# 輸出結果
print(f"總產品數量: {len(data)}")
print(f"包含『藝妓』的產品數量: {len(geisha_products)}")
print(f"無效產品數量: {len(invalid_products)}")
print("\n無效產品清單（前 5 個）：")
for msg in invalid_products[:5]:
    print(msg)
if len(invalid_products) > 5:
    print(f"... 還有 {len(invalid_products) - 5} 個無效產品")

print("\n包含『藝妓』的產品詳細資訊：")
for p, geisha_fields in geisha_products:
    item = p.get("scrape_result", {}).get("data", {}).get("data", {}).get("item", {})
    print(f"Title: {item.get('title', p.get('name', '無標題'))}")
    print(f"Link: {p.get('link', '')}")
    print("包含『藝妓』的欄位：")
    for field_name, field_value in geisha_fields.items():
        if isinstance(field_value, list):
            print(f"  {field_name}:")
            for v in field_value:
                print(f"    - {v}")
        else:
            print(f"  {field_name}: {field_value[:100]}{'...' if len(field_value) > 100 else ''}")
    print("---")