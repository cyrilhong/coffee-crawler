# -*- coding: utf-8 -*-
import sys
import os
import json
import time
import subprocess
import requests
from datetime import datetime

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8")
# 替换为你的 Scrapeless API 密钥
API_KEY = "你的_API_密钥"


def load_data(file_path):
    """载入JSON数据"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def scrape_url(url):
    """呼叫 scrape-list.py 处理单URL"""
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
        # 直接返回原始输出，清理将在 process_scrape_result 中处理
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"处理 URL {url} 时出错: {e.stderr}")
        return None


def check_task_status(task_id, api_key):
    """检查Scrapeless任务状态"""
    status_url = f"https://api.scrapeless.com/task/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    while True:
        try:
            response = requests.get(status_url, headers=headers)
            # 确保响应内容以 UTF-8 解码
            response.encoding = "utf-8"
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "completed":
                    return result
                # 使用 UTF-8 编码打印日志
                print(
                    f"任务处理中，当前状态: {result.get('status')}".encode(
                        "utf-8"
                    ).decode("utf-8")
                )
            else:
                print(f"查询失败，状态码: {response.status_code}")
                return {
                    "error": f"Task status check failed with status code {response.status_code}"
                }
        except Exception as e:
            # 捕获并打印异常，强制使用 UTF-8 编码
            error_msg = str(e)
            print(f"查询任务状态时出错: {error_msg}".encode("utf-8").decode("utf-8"))
            return {"error": error_msg}
        time.sleep(5)  # 每5秒检查一次


def process_scrape_result(raw_result):
    """处理爬取结果，使其更易读"""
    if not raw_result:
        return {"error": "Empty response"}

    try:
        # 清理前缀 "爬取结果:\n" 和换行符
        if isinstance(raw_result, str):
            # 移除可能的 "爬取结果:" 前缀
            if raw_result.startswith("爬取结果:"):
                raw_result = raw_result[len("爬取结果:") :].strip()
            # 尝试提取 JSON 部分
            start = raw_result.find("{")
            end = raw_result.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = raw_result[start:end]
                data = json.loads(json_str)
            else:
                return {
                    "error": "Invalid JSON format",
                    "raw_response": raw_result[:100] + "...",
                }
        else:
            data = raw_result

        # 检查是否有任务 ID（异步任务）
        if (
            "taskId" in data
            and "message" in data
            and data["message"] == "task in progress"
        ):
            return {"task_id": data["taskId"], "status": "task_in_progress"}

        # 检查是否有错误信息
        if "error" in data and data["error"]:
            return {"error": data.get("error"), "message": data.get("error_msg")}

        # 提取关键信息
        simplified = {
            "product_info": {
                "name": data.get("data", {}).get("item", {}).get("title"),
                "price": data.get("data", {}).get("item", {}).get("price"),
                "rating": data.get("data", {})
                .get("item", {})
                .get("item_rating", {})
                .get("rating_star"),
                "sold_count": data.get("data", {})
                .get("item", {})
                .get("historical_sold"),
            },
            "status": "success",
            "data": data,  # 直接存储解析后的 JSON 数据
        }
        return simplified

    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__,
            "raw_response": str(raw_result)[:200] + "...",
        }


def process_item(item, index):
    """处理单个商品项目"""
    print(f"\n处理第 {index+1} 笔商品:")
    print(f"商品名称: {item.get('name', 'N/A')}")
    
    # 如果是已有的数据且状态为 task_in_progress
    if isinstance(item, dict) and 'scrape_result' in item:
        scrape_result = item['scrape_result']
        if (scrape_result.get('status') == 'task_in_progress' and 
            'task_id' in scrape_result):
            # 使用 task_id 获取最终结果
            task_result = check_task_status(scrape_result['task_id'], API_KEY)
            if task_result and 'data' in task_result:
                scrape_result = process_scrape_result(task_result)
            else:
                scrape_result = {"error": "Failed to fetch task result"}
    else:
        # 原有的处理逻辑
        url = item.get('link')
        scrape_result = {"status": "pending", "error": None}
        if url:
            try:
                initial_response = scrape_url(url)
                if initial_response:
                    scrape_result = process_scrape_result(initial_response)
            except Exception as e:
                print(f"处理商品時出錯: {str(e)}")
                scrape_result = {"error": str(e), "type": type(e).__name__}
    
    processed_data = {
        'name': item.get('name'),
        'price': item.get('price'),
        'sold_count': item.get('sold_count'),
        'link': item.get('link'),
        'scrape_result': scrape_result,
        'timestamp': datetime.now().isoformat()
    }
    return processed_data

def main():
    input_file = "/Users/cyril/Documents/git/coffee-crawler/shopee-coffee.json"
    output_file = "/Users/cyril/Documents/git/coffee-crawler/shopee_processed_results-all.json"

    print("開始處理Shopee商品數據")
    data = load_data(input_file)
    results = []

    for index, item in enumerate(data):
        try:
            result = process_item(item, index)
            results.append(result)
            time.sleep(1)  # 增加延遲時間，避免請求過快
        except Exception as e:
            print(f"處理第 {index+1} 筆商品時出錯: {str(e)}")
            continue

    save_results(results, output_file)
    print(f"處理完成，共處理 {len(results)} 筆商品數據")


def save_results(results, output_file):
    """保存处理结果"""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到 {output_file}")


if __name__ == "__main__":
    main()
