from doctest import debug
import json
from datetime import datetime
import re

def load_json_data(file_path):
    """載入 JSON 數據"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_sold_count(s):
    s = s.replace('已售出', '').replace(',', '').strip()
    if '萬' in s:
        num = float(s.replace('萬', ''))
        return int(num * 10000)
    try:
        return int(s)
    except ValueError:
        return None

def update_sold_count():
    # 載入兩個文件
    source_file = "/Users/cyril/Documents/git/coffee-crawler/shopee-2025-04-18.json"
    target_file = "/Users/cyril/Documents/git/coffee-crawler/shopee_processed_results-all.json"
    
    source_data = load_json_data(source_file)
    target_data = load_json_data(target_file)
    
    # 建立連結到已售出量的映射
    sold_count_map = {}
    for item in source_data:
        if '已售出量' in item:
            sold_count_str = item['已售出量']
            if isinstance(sold_count_str, str) and '已售出' in sold_count_str:
                sold_count = parse_sold_count(sold_count_str)
                if sold_count is not None:
                    sold_count_map[item['name']] = sold_count
                    print(f"處理商品: {item.get('name')} - 售出量: {sold_count}")
                else:
                    print(f"無法解析售出量: {sold_count_str}")


    # 更新目標文件中的 sold_count
    updated_count = 0
    for item in target_data:
        name = item.get('name')
        if name in sold_count_map:
            item['sold_count'] = sold_count_map[name]
            updated_count += 1
            print(f"更新商品: {item.get('name')} - 售出量: {sold_count_map[name]}")
    
    # 保存更新後的數據
    with open(target_file, 'w', encoding='utf-8') as f:
        json.dump(target_data, f, ensure_ascii=False, indent=2)
    
    print(f"更新完成！共更新了 {updated_count} 筆數據")

if __name__ == "__main__":
    print("開始更新 sold_count...")
    update_sold_count()