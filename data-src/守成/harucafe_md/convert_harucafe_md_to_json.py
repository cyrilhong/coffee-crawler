import os
import re
import json

COUNTRY_MAP = {
    '衣索比亞': 'Ethiopia',
    '肯亞': 'Kenya',
    '巴拿馬': 'Panama',
    '哥倫比亞': 'Colombia',
    '哥斯大黎加': 'Costa Rica',
    '巴西': 'Brazil',
    '厄瓜多': 'Ecuador',
    '坦尚尼亞': 'Tanzania',
    '夏威夷': 'Hawaii',
    '印度': 'India',
    '尼加拉瓜': 'Nicaragua',
    '烏干達': 'Uganda',
    '瓜地馬拉': 'Guatemala',
    '葉門': 'Yemen',
    '薩爾瓦多': 'El Salvador',
    '巴布亞新幾內亞': 'Papua New Guinea',
    '牙買加': 'Jamaica',
}

def extract_products(md_text, url):
    # 以 **產品名稱** 為分隔，分割多個產品
    blocks = re.split(r'\*\*(.+?)\*\*', md_text)
    products = []
    for i in range(1, len(blocks), 2):
        title = blocks[i].strip()
        content = blocks[i+1] if i+1 < len(blocks) else ''
        # 解析主體資訊
        country = ''
        region = ''
        name = title
        flavor = ''
        m_country = re.search(r'■\s*國家：([^\n]+)', content)
        m_region = re.search(r'■\s*產區：([^\n]+)', content)
        m_flavor = re.search(r'■\s*風味描述：\*\*([^\*]+)\*\*([^\n]*)', content)
        if m_country:
            country = m_country.group(1).strip()
        if m_region:
            region = m_region.group(1).strip().split('，')[0]
        if m_flavor:
            flavor = m_flavor.group(1).strip() + m_flavor.group(2).strip()
        eng_name = COUNTRY_MAP.get(country, country)
        products.append({
            "country": country,
            "eng_name": eng_name,
            "region": region,
            "name": name,
            "flavor": flavor,
            "price_info": {"units": []},
            "link": url
        })
    return products

result = []
root = os.path.dirname(__file__)
for fname in os.listdir(root):
    if fname.endswith('.md'):
        with open(os.path.join(root, fname), encoding='utf-8') as f:
            text = f.read()
        # 取出原始連結
        m_url = re.search(r'\[原始連結\]\(([^\)]+)\)', text)
        url = m_url.group(1) if m_url else ''
        result.extend(extract_products(text, url))

with open(os.path.join(root, 'harucafe_md.json'), 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print('Done!')
