import requests
import json
from pathlib import Path
import time
import re

# 設定輸入的Markdown檔案路徑
input_md = Path("/Users/cyril/Documents/git/coffee-crawler/黑金/md_output/cpip_coffee_1744997283.md")
output_dir = Path("/Users/cyril/Documents/git/coffee-crawler/黑金/md_output")
output_dir.mkdir(exist_ok=True)

def extract_links_from_md(md_file):
    """從Markdown檔案中提取所有連結"""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    # 使用正則表達式提取Markdown中的連結
    return re.findall(r'\((https?://[^\s]+)\)', content)

def get_markdown_from_jina(url):
    try:
        jina_url = f"https://r.jina.ai/{url}"
        response = requests.get(jina_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"從Jina Reader獲取 {url} 時出錯: {str(e)}")
        return None

# 從Markdown檔案提取所有連結
links = extract_links_from_md(input_md)

for idx, link in enumerate(links):
    # 獲取Markdown內容
    md_content = get_markdown_from_jina(link)
    if not md_content:
        continue
    
    # 創建Markdown文件 - 使用連結的數字編號作為文件名
    filename = f"product_{idx+1}.md"
    filepath = output_dir / filename
    
    # 直接寫入從Jina獲取的完整Markdown內容
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"已保存: {filename}")
    time.sleep(1)  # 禮貌爬取間隔

print("爬取完成!")