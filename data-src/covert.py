import pandas as pd

# 從0418.txt讀取數據
with open('/Users/cyril/Documents/git/coffee-crawler/0418.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 解析數據
data = []
for line in lines[1:]:  # 跳過標題行
    parts = line.strip().split('\t')
    if len(parts) >= 5:
        data.append(parts[:5])  # 只取前5列

# 創建DataFrame
df = pd.DataFrame(data, columns=['link', 'image', 'name', 'price', 'sold'])

# 保存為Excel
df.to_excel('/Users/cyril/Documents/git/coffee-crawler/shopee-04-18.xlsx', index=False)
print(f'已成功轉換 {len(df)} 條記錄到 Excel 文件')