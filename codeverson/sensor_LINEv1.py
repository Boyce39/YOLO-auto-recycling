import time
from gpiozero import DistanceSensor
import requests
from datetime import datetime

LINETOKEN = "d4L2fzNyW3E2iV7gDISdenfz8MGsyMzJaSBPvqCBxP4"

TRIG = 5 
ECHO_GPIO= [6, 13, 26, 16]  

HEIGHT = 50  
FULL = 10  

trash_types = {"1": "紙類", "2": "塑膠", "3": "金屬", "4": "一般"}

def garbage_levels():
    status = []

    for i, echo_pin in enumerate(ECHO_GPIO):
        
        with DistanceSensor(echo=echo_pin, trigger=TRIG) as sensor:
            time.sleep(0.1)  
            distance = sensor.distance * 100  

        trash_type = trash_types.get(str(i+1), f"垃圾桶 {i+1}")

        nowtime = datetime.now().strftime("%Y%m%d_%H%M%S") 

        if distance <= FULL:
            status.append(f"🚨 {trash_type} 已滿！請清理！現在時間:{nowtime}")
        else:
            status.append(f"✅ {trash_type} 正常，距離: {distance:.1f} cm 現在時間:{nowtime}")

    return status

def send_line(message):
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINETOKEN}"}
    data = {
        "message": message,}
        #"stickerPackageId": "446",  # LINE 官方免費貼圖
        #"stickerId": "1988"
    #}

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        print("✅ LINE 訊息發送成功！")
    else:
        print(f"⚠️ 發送失敗，錯誤碼: {response.status_code}，錯誤內容: {response.text}")

try:
    while True:
        levels = garbage_levels() 
        for level in levels:
            print(level)  
            send_line(level) 

        print("="*40) 
        time.sleep(60)  
except KeyboardInterrupt:
    print("🛑 程式已停止")
