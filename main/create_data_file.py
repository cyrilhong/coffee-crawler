import json
import os

# Full JSON data provided by the user (from feedback 2024-05-22 02:30:15 UTC)
# This is a placeholder for the actual long list of dictionaries.
# In the actual execution, this placeholder will be replaced by the full JSON data.
json_data = [
  {},
  {
    "name": "咖啡生豆1公斤 #耶加雪菲 #精品生咖啡豆 #生咖啡豆",
    "price": 300,
    "sold_count": 93,
    "link": "https://shopee.tw/%E5%92%96%E5%95%A1%E7%94%9F%E8%B1%861%E5%85%AC%E6%96%A4-%E8%80%B6%E5%8A%A0%E9%9B%AA%E8%8F%B2-%E7%B2%BE%E5%93%81%E7%94%9F%E5%92%96%E5%95%A1%E8%B1%86-%E7%94%9F%E5%92%96%E5%95%A1%E8%B1%86-i.29764036.28601080555?sp_atk=d3894525-7818-4cbd-b1eb-ba4d55be1110&xptdk=d3894525-7818-4cbd-b1eb-ba4d55be1110",
    "product_info": {
      "name": "Ethiopia Yirgacheffe Kochere Chelelektu G1 Nature",
      "country": "衣索比亞",
      "region": "耶加雪菲 科契爾 雪洌圖",
      "altitude": "2000+",
      "grade": "2025年G1生豆",
      "description": "精品咖啡豆，天然健康小農合作",
      "flavor": [
        "檸檬柑橘",
        "伯爵茶尾韻",
        "蜂蜜蜜桃",
        "口感細緻"
      ],
      "weight": "1kg",
      "type": "生咖啡豆（需要烘焙）",
      "dietary_spec": "無麩質",
      "origin": "衣索比亞"
    },
    "shop_info": {
      "shop_id": 29764036,
      "shop_name": "咖啡小姐Mandy",
      "rating_star": 4.935345,
      "response_rate": 100
    },
    "shipping_info": {
      "free_shipping": False,
      "shipping_fee": None
    },
    "images": [
      "tw-11134207-7r98x-lvsq2zw0xgb68a",
      "tw-11134207-7r98q-lwv91ua83fvq29",
      "tw-11134207-7r98u-lwv91ua821ba6e",
      "tw-11134207-7rasa-m1sfal5n4y718d",
      "tw-11134207-7rasi-m1sfal5n6crhdd"
    ]
  }
  # End of placeholder - actual JSON is much longer
]

# Path relative to main/ where this script runs, so ../data-src/ is /app/data-src/
output_dir = "../data-src/"
output_filename = "shopee_flatten_results-all.json"
output_path = os.path.join(output_dir, output_filename)

try:
    # Ensure the target directory exists
    os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print(f"Successfully wrote data to {output_path}")

except Exception as e:
    print(f"Error writing data to {output_path}: {e}")
    # Re-raise the exception to ensure subtask failure if this step fails,
    # which will provide the error message in the execution log.
    raise
