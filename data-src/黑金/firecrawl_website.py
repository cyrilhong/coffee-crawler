from firecrawl import FirecrawlApp
from pathlib import Path
import time

app = FirecrawlApp(api_key="fc-dcce18b9c1d048efa4baf7d05d07e83f")

base_url = "https://blackgold.tw/stock/"
output_dir = Path("/Users/cyril/Documents/git/coffee-crawler/黑金/md_output")
output_dir.mkdir(exist_ok=True)

try:
    scrape_result = app.scrape_url(
        base_url,
        formats=["markdown"],  # 修改為markdown格式
    )
    
    # 生成文件名
    timestamp = int(time.time())
    filename = f"cpip_coffee_{timestamp}.md"
    filepath = output_dir / filename
    
    # 寫入Markdown文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(scrape_result.markdown)
    
    print(f"結果已保存至: {filepath}")

except Exception as e:
    print(f"爬取失敗：{e}")
    exit()

print("爬取完成！")
