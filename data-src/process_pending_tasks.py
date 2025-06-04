import json
import time
from datetime import datetime
import requests
import subprocess

API_KEY = "sk_jfR6JY5CsoV3s3HbaiciOMpOkyz53GnWTv0sIwQ2vDsLU9PvfKKyUDNMeG4GCo2M"

def load_json_data(file_path):
    """載入 JSON 數據"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def scrape_url(url):
    """呼叫 scrape-list.py 處理單URL"""
    try:
        result = subprocess.run(
            [
                "python3",
                "/Users/cyril/Documents/git/coffee-crawler/scrape-list.py",
                url,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"處理 URL {url} 時出錯: {e.stderr}")
        return None

def process_scrape_result(result):
    """處理爬取結果"""
    if not result:
        return {"error": "Empty response"}

    try:
        # 清理前綴和換行符
        if isinstance(result, str):
            if result.startswith("爬取結果:"):
                result = result[len("爬取結果:"):].strip()
            start = result.find("{")
            end = result.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = result[start:end]
                result = json.loads(json_str)

        simplified = {
            "product_info": {
                "name": result.get("data", {}).get("item", {}).get("title"),
                "price": result.get("data", {}).get("item", {}).get("price"),
                "rating": result.get("data", {}).get("item", {}).get("item_rating", {}).get("rating_star"),
                "sold_count": result.get("data", {}).get("item", {}).get("historical_sold"),
            },
            "status": "success",
            "data": result
        }
        return simplified
    except Exception as e:
        return {"error": str(e)}

def update_pending_tasks(file_path):
    """更新待處理的任務"""
    data = load_json_data(file_path)
    updated = False

    for item in data:
        if (isinstance(item.get('scrape_result'), dict) and 
            item['scrape_result'].get('status') == 'task_in_progress'):
            
            print(f"重新爬取商品: {item.get('name', 'Unknown')}")
            url = item.get('link')
            
            if url:
                result = scrape_url(url)
                if result:
                    processed_result = process_scrape_result(result)
                    item['scrape_result'] = processed_result
                    item['timestamp'] = datetime.now().isoformat()
                    updated = True
                    print("更新成功")
                else:
                    print(f"爬取失敗: {url}")
            
            time.sleep(2)  # 避免請求過快

    if updated:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("文件已更新")
    else:
        print("沒有需要更新的任務")

def main():
    file_path = "/Users/cyril/Documents/git/coffee-crawler/shopee_processed_results-all.json"
    print("開始重新爬取未完成的任務...")
    update_pending_tasks(file_path)
    print("處理完成")

if __name__ == "__main__":
    main()