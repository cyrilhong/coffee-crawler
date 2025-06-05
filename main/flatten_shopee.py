from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import time
from groq import Groq
import re

GROG_API_KEY = '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'

def extract_json_from_llm(content):
    # 先找 markdown 格式
    match = re.search(r"```json\s*([\s\S]+?)```", content)
    if match:
        json_str = match.group(1)
        # 嘗試只取第一個完整大括號區塊
        brace_match = re.search(r"({[\s\S]+})", json_str)
        if brace_match:
            return brace_match.group(1)
        return json_str
    # 再找最外層大括號
    match = re.search(r"({[\s\S]+})", content)
    if match:
        return match.group(1)
    return None

def ask_llm_to_flatten(item, client):
    prompt = (
        "這是一筆 Shopee 商品原始資料，請幫我展平成適合 RAG 檢索的欄位，回傳一個有意義欄位的 JSON dict，欄位要有意義、不要遺漏重要資訊：\n"
        f"{json.dumps(item, ensure_ascii=False)}"
    )
    for _ in range(3):  # 最多重試3次
        try:
            completion = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=1,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
                stop=None,
            )
            content = completion.choices[0].message.content
            print("LLM回傳內容：", content)
            json_str = extract_json_from_llm(content)
            if json_str:
                try:
                    return json.loads(json_str)
                except Exception as e:
                    print("JSON loads 失敗，嘗試修剪內容：", e)
                    # 嘗試只取第一個大括號區塊
                    brace_match = re.search(r"({[\s\S]+})", json_str)
                    if brace_match:
                        try:
                            return json.loads(brace_match.group(1))
                        except Exception as e2:
                            print("再次 loads 失敗：", e2)
            print("無法抽取 JSON 區塊，回傳空 dict")
            return {}
        except Exception as e:
            print("解析 LLM 回傳失敗或API錯誤，重試中：", e)
            time.sleep(2)
    return {}

def main():
    client = Groq(api_key=GROG_API_KEY)
    src_path = os.path.join(os.path.dirname(__file__), '../data-src/shopee_processed_results-all.json')
    dst_path = os.path.join(os.path.dirname(__file__), '../data-src/shopee_flatten_results-all.json')
    with open(src_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # data = data[:50]  # 只處理前50筆
    flat_data = [None] * len(data)
    def task(i, item):
        print(f"處理第 {i+1} 筆...")
        return i, ask_llm_to_flatten(item, client)
    with ThreadPoolExecutor(max_workers=10) as executor:  # 10條線程，安全值
        futures = [executor.submit(task, i, item) for i, item in enumerate(data)]
        for future in as_completed(futures):
            i, flat = future.result()
            flat_data[i] = flat
    with open(dst_path, 'w', encoding='utf-8') as f:
        json.dump(flat_data, f, ensure_ascii=False, indent=2)
    print(f"前50筆 flatten 完成，已存檔：{dst_path}")

if __name__ == '__main__':
    main()
