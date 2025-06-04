import json
import requests
import sys

class Payload:
    def __init__(self, actor, input_data):
        self.actor = actor
        self.input = input_data

def send_request(src):
    host = "api.scrapeless.com"
    url = f"https://{host}/api/v1/scraper/request"
    token = "sk_jfR6JY5CsoV3s3HbaiciOMpOkyz53GnWTv0sIwQ2vDsLU9PvfKKyUDNMeG4GCo2M"

    headers = {
        "x-api-token": token,
        "Content-Type": "application/json"
    }

    input_data = {
        "url": src
    }

    payload = Payload("scraper.shopee", input_data)

    json_payload = json.dumps(payload.__dict__)

    response = requests.post(url, headers=headers, data=json_payload)

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return None

    return response.json()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("請提供要爬取的URL作為參數")
        print("使用方法: python scrape-list.py <URL>")
        sys.exit(1)
    
    src_url = sys.argv[1]
    result = send_request(src_url)
    
    if result:
        print("爬取結果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))