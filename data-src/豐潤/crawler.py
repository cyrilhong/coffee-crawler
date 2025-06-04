import requests
import json
from pathlib import Path
import time

# 讀取JSON文件
with open('./fengjen-2025-04-19.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# 創建存儲目錄
output_dir = Path('./fengjen_md')
output_dir.mkdir(exist_ok=True)

def get_markdown_from_jina(url):
    try:
        jina_url = f"https://r.jina.ai/{url}"
        response = requests.get(jina_url)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"從Jina Reader獲取 {url} 時出錯: {str(e)}")
        return None

for product in products:
    # 獲取Markdown內容
    md_content = get_markdown_from_jina(product['link'])
    if not md_content:
        continue
    
    # 創建Markdown文件 - 使用產品名稱作為文件名
    filename = f"{product['name'].replace(' ', '_').replace('/', '_')}.md"
    filepath = output_dir / filename
    
    # 直接寫入從Jina獲取的完整Markdown內容
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"已保存: {filename}")
    time.sleep(1)  # 禮貌爬取間隔

print("爬取完成!")