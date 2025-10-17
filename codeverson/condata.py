import sqlite3

def save_trash_classification(category):
    conn = sqlite3.connect("garbage_data.db")
    cursor = conn.cursor()
    
    # 插入資料
    cursor.execute("INSERT INTO trash_log (category) VALUES (?)", (category,))
    
    conn.commit()
    conn.close()
    print(f"✅ 已記錄分類: {category}")

def get_trash_data():
    conn = sqlite3.connect("garbage_data.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM trash_log")
    rows = cursor.fetchall()
    
    conn.close()
    return rows

# 測試查詢
data = get_trash_data()
for row in data:
    print(row)

# 測試插入
#save_trash_classification("塑膠")
#save_trash_classification("紙類")
#save_trash_classification("金屬")
