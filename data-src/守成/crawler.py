import requests
import json
from pathlib import Path
import time

# 讀取JSON文件
with open('/Users/cyril/Documents/git/coffee-crawler/守成/harucafe-2025-04-19.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# 創建存儲目錄
output_dir = Path('/Users/cyril/Documents/git/coffee-crawler/守成/harucafe_md')
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
    
    # 創建Markdown文件
    filename = f"{product['country']}_{product['name'].split('　')[0].replace(' ', '_')}.md"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        # 寫入基本資訊
        f.write(f"# {product['name'].split('　')[0]}\n\n")
        f.write(f"## 基本資訊\n")
        f.write(f"- 國家: {product['country']}\n")
        f.write(f"- 等級: {product.get('grade', '無')}\n")
        f.write(f"- 處理法: {product['process']}\n")
        f.write(f"- 包裝: {product['package']}\n\n")
        
        # 寫入從Jina獲取的Markdown內容
        f.write(md_content)
        
        # 添加原始連結
        f.write(f"\n\n[原始連結]({product['link']})")
    
    print(f"已保存: {filename}")
    time.sleep(1)  # 禮貌爬取間隔

print("爬取完成!")