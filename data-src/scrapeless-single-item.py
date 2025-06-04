import json
import requests

class Payload:
    def __init__(self, actor, input_data):
        self.actor = actor
        self.input = input_data

def send_request():
    host = "api.scrapeless.com"
    url = f"https://{host}/api/v1/scraper/request"
    token = "sk_jfR6JY5CsoV3s3HbaiciOMpOkyz53GnWTv0sIwQ2vDsLU9PvfKKyUDNMeG4GCo2M"

    headers = {
        "x-api-token": token
    }

    input_data = {
        "url": "https://shopee.tw/%E9%A6%AC%E6%8B%89%E5%A8%81-%E8%97%9D%E4%BC%8E-%E6%B0%B4%E6%B4%97%EF%BD%9C%E7%99%BD%E8%9C%9C%EF%BD%9C%E6%97%A5%E6%9B%AC-%E8%97%9D%E5%A6%93%E5%92%96%E5%95%A1-%E5%B9%B3%E5%83%B9-%E6%89%B9%E7%99%BC-%E7%94%9F%E8%B1%86500%E5%85%8B-i.1029513055.20482158087?sp_atk=129295b4-e14a-4947-adde-e231b806a543&xptdk=129295b4-e14a-4947-adde-e231b806a543"
    }

    payload = Payload("scraper.shopee", input_data)

    json_payload = json.dumps(payload.__dict__)

    response = requests.post(url, headers=headers, data=json_payload)

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return

    print("body", response.text)

if __name__ == "__main__":
    send_request()