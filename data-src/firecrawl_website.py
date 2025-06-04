from firecrawl import FirecrawlApp
from datetime import datetime
import time
import re  # 新增正則表達式模組

app = FirecrawlApp(api_key="fc-dcce18b9c1d048efa4baf7d05d07e83f")

base_url = "https://cpip.tw/product-category/%E5%92%96%E5%95%A1%E7%94%9F%E8%B1%86/"
page = 1
max_empty_pages = 2  # 連續空頁面最大數量
empty_count = 0

while empty_count < max_empty_pages:
    current_url = f"{base_url}page/{page}/" if page > 1 else base_url
    print(f"正在爬取: {current_url}")
    
    try:
        scrape_result = app.scrape_url(
            current_url,
            formats=["markdown"],
        )
        
        # 檢查是否有有效內容
        if scrape_result and hasattr(scrape_result, 'markdown') and len(scrape_result.markdown.strip()) > 100:
            empty_count = 0  # 重置空頁計數器
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"/Users/cyril/Documents/git/coffee-crawler/cpip_coffee_p{page}_{timestamp}.md"
            
            with open(filename, 'w', encoding='utf-8') as md_file:
                md_file.write(scrape_result.markdown)
            
            print(f"第 {page} 頁 Markdown 已保存至: {filename}")
            page += 1
        else:
            empty_count += 1
            print(f"第 {page} 頁無有效內容 (連續空頁: {empty_count}/{max_empty_pages})")
            page += 1
        
        time.sleep(2)  # 禮貌性延遲
    
    except Exception as e:
        print(f"爬取第 {page} 頁時出錯: {str(e)}")
        empty_count += 1

print("爬取完成！")
