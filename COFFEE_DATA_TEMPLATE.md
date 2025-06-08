# Coffee Data 統一格式自動轉換說明

## 目標
將 `data-src` 目錄下所有咖啡資料（包含 json、md 等來源），自動轉換為統一格式，並合併輸出成一個 `all_coffee_data.json` 檔案。

## 統一資料格式範例

```json
{
  "product_code": "O25008",
  "year": "2025",
  "new": true,
  "name": "巴西 喜哈多 NY2, Cerrado, 17/18, SS FC 日曬",
  "eng_name": "Brasil Cerrado NY2, Cerrado, 17/18, SS FC Natural",
  "country": "巴西",
  "category": "商業用配豆",
  "process": "日曬",
  "specs": {
    "moisture": "10.5%",
    "density": "789 g/l"
  },
  "description": "巧克力、堅果、開心果、杏仁、濃郁甘醇",
  "price_info": {
    "units": [
      {"type": "散裝", "weight": "5KG", "price": 370},
      {"type": "袋裝", "weight": "30KG", "price": 340}
    ]
  }
}
```

## 自動化流程需求

1. **遍歷 `data-src` 目錄下所有子目錄與檔案**，自動判斷來源格式（json、md）。
2. **解析並萃取資料**，將各來源欄位對應到統一格式。
3. **缺少欄位時自動補空值或預設值**（如 `specs`、`price_info.units`）。
4. **所有資料合併成一個陣列**，輸出到 `all_coffee_data.json`。
5. **保留原始資料的最大資訊量**，如有特殊欄位可額外備註。

## 注意事項

- 若來源資料有多筆，請全部合併進同一個 json 陣列。
- 若來源資料欄位命名不同，請自動對應（如 `description`、`flavor`、`杯測資料`）。
- 若來源資料無 `product_code`，可自動產生或留空。
- 若來源資料無價格資訊，`price_info.units` 請設為空陣列。
- 若來源資料無 `specs`，請設為空物件 `{}`。

## 執行成果

- 產生一個 `all_coffee_data.json`，內容為統一格式的咖啡資料陣列。
- 可供後續資料分析、查詢、前端展示等用途。

---

如需進一步自動化腳本或有特殊規則，請依本說明執行或補充需求。

---

如需調整格式或欄位，請於本說明文件補充說明。

---

這份說明可直接交給 code agent，讓其自動化處理後續所有資料轉換與合併工作。
