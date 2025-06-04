import json
import requests
from datetime import datetime
from urllib.parse import urlencode

class ScrapingBeeShopee:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = 'https://app.scrapingbee.com/api/v1/'

    def scrape_shopee(self, keyword, page):
        base_url = 'https://shopee.tw/api/v4/search/search_items'
        params = {
            'by': 'relevancy',
            'keyword': keyword,
            'limit': 60,
            'newest': (page - 1) * 60,
            'order': 'desc',
            'page_type': 'search',
            'scenario': 'PAGE_GLOBAL_SEARCH',
            'version': 2
        }
        url = f'{base_url}?{urlencode(params)}'
        scrapingbee_params = {
            'api_key': self.api_key,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'true',
            'country_code': 'TW',
            'wait': '2000',
            'block_resources': 'false',
            'custom_google': 'true'
        }
        response = requests.get(self.base_url, params=scrapingbee_params)
        return response.json()

    def parse_data(self, data):
        items = data.get('items', [])
        results = []
        for item in items:
            results.append({
                'name': item.get('name'),
                'price': item.get('price'),
                'seller': item.get('shop_name'),
                'location': item.get('shop_location'),
                'rating': item.get('item_rating', {}).get('rating_star'),
                'sold': item.get('historical_sold'),
                'stock': item.get('stock'),
                'likes': item.get('liked_count'),
                'link': f"https://shopee.tw/product/{item.get('shopid')}/{item.get('itemid')}",
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        return results

    def save_data(self, data, filename):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    API_KEY = 'IU0RPIBEDS7TCYEZADDBVKX6WZEEWJU8G95Q35Y8FXL1HZDEY89DEJQEBI88SI3XWFI5FCK0PUCVWW0U'
    scraper = ScrapingBeeShopee(API_KEY)
    data = scraper.scrape_shopee('咖啡生豆', 1)
    parsed_data = scraper.parse_data(data)
    scraper.save_data(parsed_data, 'scrapingbee_shopee_data.json')