import scrapy
import json
from urllib.parse import urlencode

class ShopeeCoffeeSpider(scrapy.Spider):
    name = "shopee_coffee"
    allowed_domains = ["shopee.tw"]
    
    def start_requests(self):
        base_url = "https://shopee.tw/api/v4/search/search_items"
        params = {
            'by': 'relevancy',
            'keyword': '咖啡生豆',
            'limit': 60,
            'newest': 0,
            'order': 'desc',
            'page_type': 'search',
            'scenario': 'PAGE_GLOBAL_SEARCH',
            'version': 2
        }
        
        # 爬取前5頁
        for page in range(5):
            params['newest'] = page * 60
            url = f"{base_url}?{urlencode(params)}"
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
                    'Referer': 'https://shopee.tw/search?keyword=咖啡生豆'
                }
            )
    
    def parse(self, response):
        try:
            data = json.loads(response.text)
            items = data.get('items', [])
            
            for item in items:
                item_basic = item.get('item_basic', {})
                yield {
                    'name': item_basic.get('name'),
                    'price': item_basic.get('price') / 100000 if item_basic.get('price') else None,
                    'historical_sold': item_basic.get('historical_sold'),
                    'shop_location': item_basic.get('shop_location'),
                    'rating_star': item_basic.get('item_rating', {}).get('rating_star'),
                    'shop_name': item_basic.get('shop_name'),
                    'stock': item_basic.get('stock'),
                    'liked_count': item_basic.get('liked_count')
                }
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON from response: {response.url}")
        except Exception as e:
            self.logger.error(f"Error processing response from {response.url}: {str(e)}")
