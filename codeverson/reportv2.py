import sqlite3
import requests

LINETOKEN = "naobDbheaBWNXenoF04pMkG7iwyBqQXhRc1SdDalm89"

def get_run_data():
    conn = sqlite3.connect("garbage_data.db")
    cursor = conn.cursor()

    cursor.execute("SELECT category, COUNT(*) FROM trash_log")
    trash_data = cursor.fetchall()

    cursor.execute("SELECT bin_type, COUNT(*) FROM trash_full")
    full_data = cursor.fetchall()

    conn.close()
    return trash_data, full_data


def generate_report():
    trash_data, full_data = get_run_data()
    
    message = "📊 本次運行的垃圾分類數據：\n"
    for row in trash_data:
        if row[1]==0:
            message += f"很抱歉本次無數據\n"
        else:
            message += f"{row[0]}: {row[1]} 次\n"

    message += "\n🗑 本次運行的垃圾桶滿溢狀態：\n"
    for row in full_data:
        if row[1]==0:
            message += f"很抱歉本次無數據\n"
        else:
            message += f"{row[0]}: {row[1]} 次\n"
            
    return message

def send_line_report():
    message = generate_report()
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINETOKEN}"}
    data = {"message": message}

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        print("✅ 本次數據已發送至 LINE！")
    else:
        print(f"⚠️ 發送失敗，錯誤碼: {response.status_code}")

def clear_old_data():
    conn = sqlite3.connect("garbage_data.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trash_log")
    cursor.execute("DELETE FROM trash_full")
    conn.commit()
    conn.close()

send_line_report()
#clear_old_data()
