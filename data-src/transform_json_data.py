import json
import os
from pathlib import Path
import re
import unicodedata

COFFEE_TEMPLATE = {
  "product_code": "", "year": "2025", "new": False, "name": "", "eng_name": "",
  "country": "", "category": "", "process": "", "specs": {}, "description": "",
  "price_info": {"units": [] }
}

ALL_FILES_TO_PROCESS = [
    "data-src/scrapeless_results.json", "data-src/scrapingbee_shopee_data.json",
    "data-src/shopee-2025-04-18.json", "data-src/shopee-coffee.json",
    "data-src/shopee_api_results.json", "data-src/克菈菈/2025-05.json",
    "data-src/圓石/2025-05.json", "data-src/守成/harucafe-2025-04-19.json",
    "data-src/禾新/google-2025-05-14.json", "data-src/粉紅森林/粉紅森林_2025_05_報價清單.json",
    "data-src/紅沐/2025-05.json", "data-src/聯傑/聯傑咖啡_2025_05_報價清單.json",
    "data-src/萬友/2025-05-14.json", "data-src/蕭邦之夜/2025-05.json",
    "data-src/豆超/202505.json", "data-src/豐潤/fengjen-2025-04-19.json",
    "data-src/采成/20250506.json", "data-src/雅柏/2025-05.json"
]

# Single ASCII-only directory for all outputs
FINAL_OUTPUT_DIR = Path("data-src/all_formatted_outputs")

def sanitize_filename_component(component):
    """Sanitizes a single filename component to be ASCII-safe for tool interactions."""
    if component is None: return ""
    # Normalize Unicode characters to their decomposed form
    nfkd_form = unicodedata.normalize('NFKD', str(component))
    # Keep only ASCII characters
    ascii_component = "".join([c for c in nfkd_form if not unicodedata.combining(c) and ord(c) < 128])
    # Replace any non-alphanumeric (besides ._ -) with underscore, keep case
    ascii_component = re.sub(r'[^\w.\-_]', '_', ascii_component)
    # Avoid empty names or names starting/ending with underscore if possible after sanitization
    if not ascii_component: return "sanitized_empty"
    return ascii_component.strip('_')


def transform_coffee_item(original_item):
    transformed = COFFEE_TEMPLATE.copy()
    transformed["specs"] = COFFEE_TEMPLATE["specs"].copy()
    transformed["price_info"] = {"units": COFFEE_TEMPLATE["price_info"]["units"][:]}

    transformed["name"] = original_item.get("name", original_item.get("品項", ""))
    transformed["country"] = original_item.get("country", original_item.get("國家", ""))
    transformed["category"] = original_item.get("region", original_item.get("產區", ""))
    process_val = original_item.get("process", original_item.get("processing", original_item.get("處理法", "")))
    transformed["process"] = process_val if process_val is not None else ""
    description_val = original_item.get("description", original_item.get("flavor", original_item.get("風味", original_item.get("杯測資料", ""))))
    transformed["description"] = description_val if description_val is not None else ""
    transformed["product_code"] = original_item.get("product_code", original_item.get("coffee_code", ""))
    transformed["eng_name"] = original_item.get("eng_name", "")

    current_specs = {}
    if "moisture" in original_item and original_item["moisture"] is not None: current_specs["moisture"] = original_item["moisture"]
    if "density" in original_item and original_item["density"] is not None: current_specs["density"] = original_item["density"]
    if "含水率" in original_item and original_item["含水率"] is not None: current_specs["moisture"] = original_item["含水率"]
    if "密度" in original_item and original_item["密度"] is not None: current_specs["density"] = original_item["密度"]
    transformed["specs"] = current_specs

    price_units = []
    clara_prices = {
        "bag_price_35kg": ("袋裝", "35KG"), "bag_price_5kg": ("散裝", "5KG"),
        "bag_price_22kg": ("袋裝", "22KG"), "bag_price_30kg": ("袋裝", "30KG"),
        "bag_price_24kg": ("袋裝", "24KG")
    }
    for key, (unit_type, weight) in clara_prices.items():
        if key in original_item and isinstance(original_item[key], dict):
            price_data = original_item[key]
            price = price_data.get("promo", price_data.get("origin"))
            if price is not None: price_units.append({"type": unit_type, "weight": weight, "price": price})

    if not price_units:
        price_keys = ["price", "價格", "售價"]
        for pk in price_keys:
            if pk in original_item and original_item[pk] is not None:
                price_val = original_item[pk]
                is_numeric = isinstance(price_val, (int, float))
                is_large_shopee_price = False
                if is_numeric and price_val > 10000: is_large_shopee_price = True
                elif isinstance(price_val, str) and price_val.isdigit() and len(price_val) > 4 : # check if it's a string of digits
                    try: # try converting to int for comparison
                        if int(price_val) > 10000: is_large_shopee_price = True
                        price_val = int(price_val) # Use the int value
                    except ValueError: pass # Not a simple int string

                if is_large_shopee_price: price_val = price_val / 100000

                price_units.append({"type": "公斤", "weight": "1KG", "price": price_val})
                break
    transformed["price_info"]["units"] = price_units

    if not transformed["price_info"]["units"] and "package" in original_item and isinstance(original_item["package"], str):
        parts = original_item["package"].split('/')
        for part_str in parts:
            part_str = part_str.strip()
            match = re.search(r"(\d+(\.\d+)?)\s*(KG|公斤)", part_str, re.IGNORECASE)
            if match:
                weight_val = match.group(1) + "KG"
                if not any(unit["weight"] == weight_val for unit in transformed["price_info"]["units"]):
                    transformed["price_info"]["units"].append({"type": "包裝", "weight": weight_val, "price": None})

    if "error" in original_item:
        transformed["name"] = "API Error"
        transformed["description"] = f"Failed to fetch: {original_item.get('original_url', '')}. Error: {original_item['error']}"
        for key_to_clear in ["country", "category", "process", "product_code", "eng_name"]: transformed[key_to_clear] = ""
        transformed["specs"] = {}; transformed["price_info"]["units"] = []

    for key, default_value in COFFEE_TEMPLATE.items():
        if key not in transformed:
            if isinstance(default_value, dict): transformed[key] = default_value.copy()
            elif isinstance(default_value, list): transformed[key] = default_value[:]
            else: transformed[key] = default_value
        elif key == "price_info" and "units" not in transformed[key]: transformed[key]["units"] = []
        elif key == "specs" and not isinstance(transformed[key], dict): transformed[key] = {}
    return transformed

def main_full():
    print("Python script started (full version).", flush=True)
    try:
        FINAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Ensured final output directory exists: {FINAL_OUTPUT_DIR}", flush=True)
    except Exception as e:
        print(f"CRITICAL: Could not create final output directory {FINAL_OUTPUT_DIR}: {e}", flush=True)
        return

    output_file_map_log = []

    for idx, file_path_str in enumerate(ALL_FILES_TO_PROCESS):
        original_path_obj = Path(file_path_str)
        print(f"Processing file {idx+1}/{len(ALL_FILES_TO_PROCESS)}: {file_path_str}", flush=True)

        if not original_path_obj.exists():
            print(f"File not found: {file_path_str}. Skipping.", flush=True)
            continue

        try:
            content = original_path_obj.read_text(encoding='utf-8')
            if not content.strip():
                print(f"File is empty: {file_path_str}. Skipping.", flush=True)
                data = []
            else:
                data = json.loads(content)
        except json.JSONDecodeError as je:
            print(f"Error decoding JSON from {file_path_str}: {je}. Skipping.", flush=True)
            continue
        except Exception as e:
            print(f"Error reading file {file_path_str}: {e}. Skipping.", flush=True)
            continue

        transformed_data = []
        if isinstance(data, list):
            if not data: print(f"Input file {file_path_str} contained an empty JSON list.", flush=True)
            for item_idx_inner, item in enumerate(data):
                if isinstance(item, dict): transformed_data.append(transform_coffee_item(item))
                else: print(f"Skipping non-dict item #{item_idx_inner} from {file_path_str}: {type(item)}", flush=True)
        elif isinstance(data, dict):
            if not data: print(f"Input file {file_path_str} contained an empty JSON dictionary.", flush=True)
            transformed_data.append(transform_coffee_item(data))
        else:
            print(f"Unsupported JSON structure or empty file {file_path_str}. Type: {type(data)}. Skipping.", flush=True)
            continue

        # Create a unique, sanitized filename for storage in FINAL_OUTPUT_DIR
        # Include sanitized original directory parts to ensure uniqueness if filenames are common (e.g. "2025-05.json")
        sanitized_parent_dirs = "_".join([sanitize_filename_component(p) for p in original_path_obj.parent.parts if p != 'data-src'])
        sanitized_original_basename = sanitize_filename_component(original_path_obj.name)

        if sanitized_parent_dirs:
            unique_sanitized_name_base = f"{sanitized_parent_dirs}_{sanitized_original_basename}"
        else: # for files directly in data-src
            unique_sanitized_name_base = sanitized_original_basename

        output_filename = f"formatted-{unique_sanitized_name_base}"
        if not output_filename.endswith(".json"): # ensure .json suffix if original was not
             output_filename += ".json"

        actual_output_path = FINAL_OUTPUT_DIR / output_filename
        intended_final_path_str = str(original_path_obj.parent / f"formatted-{original_path_obj.name}")

        output_file_map_log.append(f"Actual_Saved_Path: {actual_output_path}  ==> Intended_Final_Path: {intended_final_path_str}")

        try:
            with open(actual_output_path, 'w', encoding='utf-8') as f:
                json.dump(transformed_data, f, ensure_ascii=False, indent=2)
            print(f"Successfully transformed {file_path_str} and saved to: {actual_output_path}", flush=True)
        except Exception as e:
            print(f"CRITICAL: Error writing file {actual_output_path} (from original {file_path_str}): {e}", flush=True)

    print("\n--- Output File Mapping (Actual saved path to Intended final path) ---", flush=True)
    for entry in output_file_map_log:
        print(entry, flush=True)
    print("--- End Mapping ---", flush=True)
    print("Python script finished (full version).", flush=True)

if __name__ == "__main__":
    main_full()
