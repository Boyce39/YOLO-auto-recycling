import time
import os
import requests
from gpiozero import DistanceSensor
from datetime import datetime
import sqlite3
import signal

def connect_db():
    return sqlite3.connect("garbage_data.db")

def save_trash_full(bin_type):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO trash_full (bin_type, status) VALUES (?, '滿溢')", (bin_type,))
    conn.commit()
    conn.close()
    print(f"⚠️ {bin_type} 已滿，記錄成功")

LINETOKEN = "naobDbheaBWNXenoF04pMkG7iwyBqQXhRc1SdDalm89"

TRIG = 5 
ECHO_GPIO = [6, 13, 26, 16]  
HEIGHT = 50  
FULL = 10  


trash_types = {
    "1": "紙類回收桶", 
    "2": "塑膠回收桶", 
    "3": "金屬回收桶", 
    "4": "一般垃圾桶"
}

# 🔹 啟動 `main.py`
def start_detect():
    print("🚀 啟動垃圾分類程式...")
    os.system("python3 detect.py &")  # 背景執行

# 🔹 關閉 `main.py`
def stop_detect():
    print("🛑 關閉垃圾分類程式...")
    os.system("pkill -f detect.py")  # 關閉所有 `main.py` 進程

# 🔹 監測垃圾桶狀態
def garbage_levels():
    status = []

    for i, echo_pin in enumerate(ECHO_GPIO):
        with DistanceSensor(echo=echo_pin, trigger=TRIG) as sensor:
            time.sleep(0.1)  
            distance = int(sensor.distance * 100)

        trash_type = trash_types.get(str(i+1), f"垃圾桶 {i+1}")
        nowtime = datetime.now().strftime("%Y-%m-%d %H:%M") 

        if distance <= FULL:
            status.append(f"🚨 {trash_type} 已滿！請清理！現在時間 : {nowtime}")
            send_line(f"🚨 {trash_type} 已滿！請更換垃圾袋！")
            stop_detect()  # ❌ 關閉 `main.py`
            save_trash_full(trash_type)
            reset(trash_type)  # 🔄 開始監測垃圾桶是否已清理

        #else:
        #    status.append(f"✅ {trash_type} 正常，距離: {distance:.1f} cm 現在時間 : {nowtime}")

    return status

# 🔹 發送 LINE 通知
def send_line(message):
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINETOKEN}"}
    data = {"message": message}
    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        print("✅ LINE 訊息發送成功！")
    else:
        print(f"⚠️ 發送失敗，錯誤碼: {response.status_code}，錯誤內容: {response.text}")

# 🔹 監測垃圾桶是否被清理
# 🔹 監測垃圾桶是否被清理


def reset(trash_type):
    print(f"🔍 監測 {trash_type} 是否清空...")
    
    target_bin = None

    for key, value in trash_types.items():
        if value == trash_type:
            target_bin = key  # 取得垃圾桶對應的索引
            break

    while True:
        time.sleep(10)  # 每 10 秒檢查一次

        # **只檢查這次滿溢的垃圾桶**
        target_pin = ECHO_GPIO[int(target_bin)-1]
        with DistanceSensor(echo=target_pin, trigger=TRIG) as sensor:
            time.sleep(0.1)
            distance = int(sensor.distance * 100)

        if distance > HEIGHT:
            print(f"✅ {trash_type} 已清空，系統重新啟動！")
            send_line(f"✅ {trash_type} 已清空，系統重新啟動！")
            start_detect()  # 🚀 重新啟動 `detect.py`
            return  # **結束監測**


# 🔹 主監測迴圈
try:
    start_detect()  # ✅ 啟動 `main.py`

    while True:
        levels = garbage_levels() 
        for level in levels:
            print(level)
        
        print("="*40)
        time.sleep(60)  # 每 60 秒檢查一次垃圾桶狀態

except KeyboardInterrupt:
    print("🛑 程式已停止")
    stop_detect()
    os.system("python3 report.py")