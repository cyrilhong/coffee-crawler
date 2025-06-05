import json
import uuid

def extract_info(item):
    chunks = []

    # Safely extract nested data
    # Adjusted path based on typical Shopee API structure
    item_data_container = item.get("scrape_result", {}).get("data", {})
    item_data = item_data_container.get("data", {}).get("item", {})

    # If "item" is not directly under "data.data", it might be directly under "data" or "scrape_result"
    if not item_data:
        item_data = item_data_container.get("item", {}) # Try data.item
    if not item_data: # Fallback if primary path is missing, check if item itself contains the details
        item_data = item.get("item_info", item) # Common alt key or use item directly

    # 1. Generate doc_id
    # Prioritize item_id from the most specific part of the structure
    doc_id = item_data.get("itemid", item_data.get("item_id")) # Shopee often uses "itemid"
    if not doc_id:
        doc_id = item.get("link") # Use link as a fallback
    if not doc_id: # If link is also missing
        doc_id = str(uuid.uuid4())

    # Make sure doc_id is a string for f-string formatting later
    doc_id = str(doc_id)

    name = item.get("name", "")
    price = item.get("price", "") # This is often a string like "100 - 200" or just "100"
    link = item.get("link", "")
    sold_count = item.get("sold_count", item_data.get("historical_sold", item_data.get("sold", ""))) # Prioritize specific keys

    rating_star_dict = item_data.get("item_rating", {})
    rating = rating_star_dict.get("rating_star", "") if isinstance(rating_star_dict, dict) else ""

    brand = item_data.get("brand", "")

    # Categories can be complex; try a few common paths
    categories = item_data.get("categories", [])
    category = ""
    if categories and isinstance(categories, list) and len(categories) > 0 and isinstance(categories[0], dict):
        category = categories[0].get("display_name", "")
    if not category: # Fallback
        category = item_data.get("category_name", "")


    # Shop info
    shop_info_source = item_data_container.get("data", {}).get("shop_detailed", {}) # data.data.shop_detailed
    if not shop_info_source:
        shop_info_source = item_data_container.get("shop_detailed", {}) # data.shop_detailed
    if not shop_info_source:
        shop_info_source = item_data # Fallback to item_data fields

    shop_name = shop_info_source.get("name", item_data.get("shop_name", ""))
    shop_location = item_data.get("shop_location", shop_info_source.get("shop_location",""))
    shop_rating_val = shop_info_source.get("rating_star", item_data.get("shop_rating", ""))
    shop_rating = f"{shop_rating_val:.2f}" if isinstance(shop_rating_val, float) else str(shop_rating_val)


    # Full description
    description = item_data.get("description", "")
    if not description:
        desc_paragraphs = item_data_container.get("data", {}).get("product_description", {}).get("paragraph_list", [])
        if not desc_paragraphs : # Try one level up if nested under data.data
             desc_paragraphs = item_data_container.get("product_description", {}).get("paragraph_list", [])
        description = "\n".join(
            [p.get("text", "") for p in desc_paragraphs if p.get("text")]
        )
    if not description:
        description = item_data.get("short_description", "")

    # 2. Base metadata
    base_metadata = {
        "name": name,
        "price": str(price), # Ensure price is string
        "link": link,
        "sold_count": str(sold_count), # Ensure sold_count is string
        "rating": str(rating), # Ensure rating is string
        "brand": brand,
        "category": category,
        "shop_name": shop_name,
        "shop_location": shop_location,
        "shop_rating": shop_rating,
        "original_description": description
    }

    # 3. Chunk Type 1: core_info
    core_content = (
        f"商品名稱：{name}\n"
        f"價格：{base_metadata['price']} 元\n" # Use sanitized price
        f"品牌：{brand}\n"
        f"分類：{category}\n"
        f"商店名稱：{shop_name}\n"
        f"商店評分：{shop_rating}"
    )
    chunks.append({
        "doc_id": doc_id,
        "chunk_id": f"{doc_id}_core",
        "type": "core_info",
        "content": core_content,
        "metadata": base_metadata.copy()
    })

    # 4. Chunk Type 2: description_segment
    if description and isinstance(description, str):
        segment_length = 120
        overlap = 30
        start = 0
        segment_index = 0
        # Ensure description is not empty before starting loop
        if description.strip(): # Check if description has non-whitespace characters
            while start < len(description):
                end = start + segment_length
                segment = description[start:end]
                chunks.append({
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_desc_{segment_index}",
                    "type": "description_segment",
                    "content": segment,
                    "metadata": base_metadata.copy()
                })
                segment_index += 1
                if end >= len(description):
                    break
                start += (segment_length - overlap)
                # Ensure we don't create an empty chunk if overlap makes start >= len(description)
                if start >= len(description):
                    break

    # 5. Chunk Type 3: attribute_info
    attributes = item_data.get("attributes", [])
    if attributes and isinstance(attributes, list):
        for attr_index, attr in enumerate(attributes):
            if isinstance(attr, dict):
                attr_name = attr.get('name', '')
                attr_value = attr.get('value', '')
                if attr_name and attr_value: # Only add if both name and value exist
                    chunks.append({
                        "doc_id": doc_id,
                        "chunk_id": f"{doc_id}_attr_{attr_index}",
                        "type": "attribute_info",
                        "content": f"商品屬性：{attr_name} - {attr_value}",
                        "metadata": base_metadata.copy()
                    })

    return chunks

# Main script execution
if __name__ == "__main__":
    input_filename = "../data-src/shopee_flatten_results-all.json" # Path changed to ../data-src/
    output_filename = "./output.txt" # Modified path

    try:
        with open(input_filename, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {input_filename} not found.")
        data = []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_filename}.")
        data = []

    all_chunks = []
    items_processed_count = 0
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                item_chunks = extract_info(item)
                all_chunks.extend(item_chunks)
                items_processed_count +=1
            else:
                print(f"Warning: Skipping an item that is not a dictionary: {item}")
    elif isinstance(data, dict):
        print(f"Info: JSON root is a dictionary. Attempting to find a list of items within it.")
        possible_list_keys = ['items', 'results', 'data', 'products', 'all_items']
        found_list = False
        # Check if the root dict itself is a single item structure (e.g. if the file contains only one product)
        if "itemid" in data or "item_id" in data or "name" in data: # Heuristic for single item
             print(f"Info: JSON root dictionary appears to be a single item. Processing it directly.")
             item_chunks = extract_info(data)
             all_chunks.extend(item_chunks)
             items_processed_count +=1
             found_list = True # Technically not a list, but processed as one item.

        if not found_list:
            for key in possible_list_keys:
                if key in data and isinstance(data[key], list):
                    print(f"Info: Found list of items under key '{key}'. Processing {len(data[key])} items.")
                    actual_data_list = data[key]
                    for item_in_list in actual_data_list:
                        if isinstance(item_in_list, dict):
                            item_chunks = extract_info(item_in_list)
                            all_chunks.extend(item_chunks)
                            items_processed_count +=1
                        else:
                            print(f"Warning: Skipping an item within list '{key}' that is not a dictionary: {item_in_list}")
                    found_list = True
                    break
            if not found_list:
                print(f"Error: Could not find a list of items within the root dictionary using common keys. No items processed from dictionary.")
    else:
        print(f"Warning: Expected a list of items or a dictionary containing a list from JSON, but got {type(data)}. No items will be processed.")

    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            for chunk_dict in all_chunks:
                f.write(json.dumps(chunk_dict, ensure_ascii=False) + "\n")

        if items_processed_count > 0 and all_chunks:
            print(f"Successfully processed {items_processed_count} items and generated {len(all_chunks)} chunks into {output_filename}.")
        elif items_processed_count > 0 and not all_chunks:
             print(f"Processed {items_processed_count} items, but no chunks were generated. This might be due to item structure (e.g. missing descriptions/attributes) or the items not matching expected format. Check your data and `extract_info` logic.")
        elif not data :
             print(f"No data was loaded from {input_filename}, so no chunks generated.")
        else:
            print(f"Data was loaded from {input_filename}, but no items were processed into chunks. Check the structure of your JSON file and console warnings.")

    except IOError:
        print(f"Error: Could not write to {output_filename}.")
    except Exception as e:
        print(f"An unexpected error occurred during writing or processing: {e}")
        import traceback
        traceback.print_exc()
