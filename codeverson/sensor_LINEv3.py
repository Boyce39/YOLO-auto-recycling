import time
import os
import requests
from gpiozero import DistanceSensor
from datetime import datetime
from database import save_trash_full
import signal

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
def start_main():
    print("🚀 啟動垃圾分類程式...")
    os.system("python3 /home/Desktop/yolo_project/main.py &")  # 背景執行

# 🔹 關閉 `main.py`
def stop_main():
    print("🛑 關閉垃圾分類程式...")
    os.system("pkill -f main.py")  # 關閉所有 `main.py` 進程

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
            stop_main()  # ❌ 關閉 `main.py`
            save_trash_full(trash_type)
            reset()  # 🔄 開始監測垃圾桶是否已清理

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
def reset():
    print("🔍 監測垃圾桶是否清空...")
    while True:
        time.sleep(10)  # 每 10 秒檢查一次
        
        for i, echo_pin in enumerate(ECHO_GPIO):
            with DistanceSensor(echo=echo_pin, trigger=TRIG) as sensor:
                time.sleep(0.1)  
                distance = int(sensor.distance * 100)

            if distance > HEIGHT:
                trash_type = trash_types.get(str(i+1), f"垃圾桶 {i+1}")
                print(f"✅ {trash_type} 已清空，系統重新啟動！")
                send_line(f"✅ {trash_type} 已清空，系統重新啟動！")
                start_main()  # 🚀 重新啟動 `main.py`
                return  # **結束監測**

# 🔹 主監測迴圈
try:
    start_main()  # ✅ 啟動 `main.py`

    while True:
        levels = garbage_levels() 
        for level in levels:
            print(level)
        
        print("="*40)
        time.sleep(60)  # 每 60 秒檢查一次垃圾桶狀態

except KeyboardInterrupt:
    print("🛑 程式已停止")
    os.system("python3 /home/Desktop/yolo_project/report.py")