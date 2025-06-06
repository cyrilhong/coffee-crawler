import json
import re

# 國家中英文對照表
COUNTRY_MAP = {
    '衣索比亞': 'Ethiopia',
    '肯亞': 'Kenya',
    '巴拿馬': 'Panama',
    '哥斯大黎加': 'Costa Rica',
    '巴布亞新幾內亞': 'Papua New Guinea',
    '坦尚尼亞': 'Tanzania',
    '瓜地馬拉': 'Guatemala',
    '宏都拉斯': 'Honduras',
}

# 讀取原始資料
with open('../google-2025-05-14.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)

result = []

for item in raw:
    # 1. 杯測資料label處理
    flavor = item.get('杯測資料', '')
    flavor = re.sub(r'< *編號:.*?>', '', flavor)
    flavor = re.sub(r'<編號:.*?>', '', flavor)
    flavor = re.sub(r'< *編號.*?>', '', flavor)
    flavor = re.sub(r'<.*?>', '', flavor)
    flavor = flavor.replace('售完', '').replace('特價', '').replace('每公', '').strip()

    # 2. 國家與region萃取
    name = item.get('name', '')
    country = None
    region = None
    for c in COUNTRY_MAP:
        if name.startswith(c):
            country = c
            region = name[len(c):].split()[0] if len(name) > len(c) else ''
            break
    if not country:
        country = name.split()[0]
        region = name.split()[1] if len(name.split()) > 1 else ''
    eng_name = COUNTRY_MAP.get(country, country)

    # 價格資訊
    def parse_price(val):
        try:
            return int(re.sub(r'[^0-9]', '', val))
        except:
            return None
    price_info = {
        "units": [
            {
                "origin": parse_price(item.get('3kg 價格', '')),
                "weight": "3kg",
                "promo": parse_price(item.get('3kg 價格', '')),
                "sold_out": '售完' in flavor
            },
            {
                "origin": parse_price(item.get('30kg 價格', '')),
                "weight": "30kg",
                "promo": parse_price(item.get('30kg 價格', '')),
                "sold_out": '售完' in flavor
            }
        ]
    }

    # link
    link = item.get('詳細頁面', '')

    result.append({
        "country": country,
        "eng_name": eng_name,
        "region": region,
        "name": name,
        "flavor": flavor,
        "price_info": price_info,
        "link": link
    })

with open('./cleaned_google-2025-05-14.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print('Done!')
