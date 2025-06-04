import requests
import json

def send_search_request():
    host = "api.scrapeless.com"
    url = f"https://{host}/api/v1/scraper/request"
    token = "sk_jfR6JY5CsoV3s3HbaiciOMpOkyz53GnWTv0sIwQ2vDsLU9PvfKKyUDNMeG4GCo2M"  # Replace with your API key

    headers = {
        "Content-Type": "application/json",
        "x-api-token": token
    }

    input_data = {
        "action": "shopee.search",
        "url": "https://shopee.tw/search?keyword=%E5%92%96%E5%95%A1%E7%94%9F%E8%B1%86&page=1"  # Corrected URL
    }

    payload = {
        "actor": "scraper.shopee",
        "input": input_data
    }

    json_payload = json.dumps(payload)

    response = requests.post(url, headers=headers, data=json_payload)

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return None

    print("Raw response:", response.text)
    return response.json()

def parse_search_results(response_data):
    if not response_data or "data" not in response_data:
        print("No valid data in response")
        return []

    items = response_data.get("data", {}).get("items", [])
    results = []

    for item in items:
        name = item.get("name", "N/A")
        price = item.get("price", 0) / 100000  # Shopee price is in micro-units, divide by 100000
        historical_sold = item.get("historical_sold", 0)  # Approximate reviews

        results.append({
            "name": name,
            "price": f"NT${price:.2f}",
            "reviews": historical_sold
        })

    return results

def main():
    # Send search request
    response_data = send_search_request()
    if not response_data:
        return

    # Parse results
    parsed_results = parse_search_results(response_data)
    
    # Output results
    print("\nParsed Search Results:")
    print(json.dumps(parsed_results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()