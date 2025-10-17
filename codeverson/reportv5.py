import sqlite3
import requests


LINETOKEN = "naobDbheaBWNXenoF04pMkG7iwyBqQXhRc1SdDalm89"

def connect_db():
    return sqlite3.connect("garbage_data.db")

def init_db():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trash_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT UNIQUE,  
        times INTEGER DEFAULT 0
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trash_full (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bin_type TEXT UNIQUE,
        times INTEGER DEFAULT 0
    )""")

    default_trash_types = ["紙類", "塑膠類", "金屬類", "一般垃圾"]
    for category in default_trash_types:
        cursor.execute("INSERT OR IGNORE INTO trash_log (category, times) VALUES (?, 0)", (category,))

    default_bins = ["紙類回收桶", "塑膠回收桶", "金屬回收桶", "一般垃圾桶"]
    for bin_type in default_bins:
        cursor.execute("INSERT OR IGNORE INTO trash_full (bin_type, times) VALUES (?, 0)", (bin_type,))

    conn.commit()
    conn.close()
    
#init_db()


def get_run_data():
    conn = sqlite3.connect("garbage_data.db")
    cursor = conn.cursor()

    cursor.execute("SELECT category, times FROM trash_log")
    trash_data = cursor.fetchall()

    cursor.execute("SELECT bin_type, times FROM trash_full")
    full_data = cursor.fetchall()

    conn.close()
    return trash_data, full_data


def generate_report():
    trash_data, full_data = get_run_data()

    message_trash = "\n📊 本次運行的垃圾分類數據：\n"
    has_trash_data = False
    for row in trash_data:
        category, count = row
        message_trash += f"{category}: {count} 次\n"
        if count > 0:
            has_trash_data = True

    if not has_trash_data:
        message_trash = "\n📊 本次運行的垃圾分類數據：\n"+"❌ 本次運行沒有記錄到任何垃圾分類數據。\n"

    message_full = "\n🗑 本次運行的垃圾桶滿溢狀態：\n"
    has_full_data = False 
    for row in full_data:
        bin_type, count = row
        message_full += f"{bin_type}: {count} 次\n"
        if count > 0:
            has_full_data = True

    if not has_full_data:
        message_full ="\n🗑 本次運行的垃圾桶滿溢狀態：\n"+"✅ 本次沒有垃圾桶滿溢記錄，狀況良好。\n"

    return message_trash + message_full


def send_line_report():
    message = generate_report()
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINETOKEN}"}
    data = {"message": message}

    try:
        response = requests.post(url, headers=headers, data=data)

        if response.status_code == 200:
            print("✅ 本次數據已成功發送至 LINE！")
        else:
            print(f"⚠️ 發送失敗，錯誤碼: {response.status_code}，錯誤內容: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ 發送失敗，請檢查網路連線：{e}")

def clear_old_data():
    conn = sqlite3.connect("garbage_data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE trash_log SET times = 0")
    cursor.execute("UPDATE trash_full SET times = 0")
    
    conn.commit()
    conn.close()

send_line_report()
clear_old_data()
