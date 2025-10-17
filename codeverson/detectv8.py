import cv2
import os
from ultralytics import YOLO
from datetime import datetime
from gpiozero.tones import Tone
from gpiozero import DistanceSensor, Button ,Servo,LED,TonalBuzzer
import time
import requests
import sqlite3
import warnings
warnings.filterwarnings("ignore")

model = YOLO('bestv6.pt')
sensor = DistanceSensor(echo=23, trigger=24)
last_time = 0   
flag=True
TRIG = 5 
ECHO_GPIO = [6, 13, 26, 16]  
servo_GPIO=19
HEIGHT = 50  
FULL = 10 

trash_types = {
    "1": "紙類回收桶", 
    "2": "塑膠回收桶", 
    "3": "金屬回收桶", 
    "4": "一般垃圾桶"
}

buttons = {
    "塑膠類": Button(17, pull_up=True),
    "紙類": Button(27, pull_up=True),
    "金屬類": Button(22, pull_up=True),
}
LINETOKEN = "naobDbheaBWNXenoF04pMkG7iwyBqQXhRc1SdDalm89"



def play_music():
    buzzer = TonalBuzzer(20)
    song = [
    ("E4", 0.6), ("G4", 0.6), ("E4", 0.6), ("C4", 0.6),  
    ("A3", 0.6), ("C4", 0.6), ("E4", 0.6), ("D4", 0.6),  
    ("B3", 0.6), ("D4", 0.6), ("F4", 0.6), ("E4", 0.8)   
]
    for note, duration in song:
        buzzer.play(Tone(note))
        time.sleep(duration)
    buzzer.stop()
    buzzer.close()




def waring_choose():
    buzzer = TonalBuzzer(20)
    for _ in range(2):  
        buzzer.play(Tone(880)) 
        time.sleep(0.3)  
        buzzer.stop()
        time.sleep(0.2) 
    buzzer.stop()
    buzzer.close()




def waring_full():
    buzzer = TonalBuzzer(20)
    for _ in range(3):  
        buzzer.play(Tone(880)) 
        time.sleep(0.3)  
        buzzer.stop()
        time.sleep(0.2) 
    buzzer.stop()
    buzzer.close()




def connect_db():
    return sqlite3.connect("garbage_data.db")


def open_door():
    servo = Servo(19, min_pulse_width=0.0009, max_pulse_width=0.0018)
    print("自動化系統啟動，請投入垃圾")
    servo.min()
    time.sleep(0.6)
    servo.value = None
    time.sleep(3)
    servo.max()
    time.sleep(0.6)
    servo.value = None    




def save_data(category):
    conn = connect_db()
    cursor = conn.cursor()
    # **累加該類別的次數**
    cursor.execute("UPDATE trash_log SET times = times + 1 WHERE category = ?", (category,))

    conn.commit()
    conn.close()




def save_trash_full(bin_type):
    conn = connect_db()
    cursor = conn.cursor()

    # **累加該垃圾桶的滿溢次數**
    cursor.execute("UPDATE trash_full SET times = times + 1 WHERE bin_type = ?", (bin_type,))

    conn.commit()
    conn.close()



def distance():
    return sensor.distance * 100 

def classification():
    waring_choose()
    print("⏳ 等待使用者分類（10 秒內）...否則丟往一般垃圾")

    start_time = time.time()

    while time.time() - start_time < 10:  
        for trash_type, button in buttons.items():
            if button.is_pressed:
                return trash_type  
            
        time.sleep(0.1)

    return "一般垃圾"



def run():
    os.system(f"python3 music.py &") 
    open_door()
    ledpin=18
    led=LED(ledpin)
    led.on()
    time.sleep(1)
    cap = cv2.VideoCapture(0)  
    hold = 0.6  
    ret, frame = cap.read()
    led.off()
    results = model(frame)  
    detect = []
    
    for result in results[0].boxes:
        class_id = int(result.cls)  
        confidence = float(result.conf) 
        name = {0: '金屬類', 1: '紙類', 2: '塑膠類'}.get(class_id)
        final = name if confidence >= hold else '一般垃圾'

        detect.append(final)

    img = results[0].plot()  
    nowtime = datetime.now().strftime("%Y%m%d_%H%M%S") 
    save_img = f'/home/pi/Desktop/yolo_project/run_img/偵測_{nowtime}.jpg'

    cv2.imwrite(save_img, img)  

    cap.release()

    cv2.destroyAllWindows()  

    return detect 


def detect_run():
    last_time = time.time()
    print("🔍 偵測物品掉落，開始檢測...\n")
    detected = run()
    only=True
    l=len(detected)
    generally_count=detected.count('一般垃圾')
    metal_count=detected.count('金屬類')
    plastic_count=detected.count('塑膠類')
    paper_count=detected.count('紙類')
    if l==2 and generally_count==1:
            detected.remove('一般垃圾')
            final = detected[0]
    elif  l > 2 :
        detected.remove('一般垃圾')
        l=len(detected)
        if l>1:
            for i in range(1,l):
                if detected[i-1]!=detected[i]:
                    only=False
                    break          
        if only:
            final = detected[0]
        else:
            print('檢測失敗請按壓按鈕分類')
            final = classification()
    elif '一般垃圾' in detected:
        print('檢測到一般垃圾，如果偵測錯誤請按壓按鈕分類')
        final = classification()
    elif l ==0 :
        final = classification()
    else:
        final = detected[0]
    save_data(final)
    print(f"📦 最終分類結果：{final}")
    play_music()



def garbage_levels():
    status = []
    for i, echo_pin in enumerate(ECHO_GPIO):
        with DistanceSensor(echo=echo_pin, trigger=TRIG) as sensor:
            time.sleep(0.1)  
            distance = int(sensor.distance * 100)

        trash_type = trash_types.get(str(i+1), f"垃圾桶 {i+1}")
        nowtime = datetime.now().strftime("%Y-%m-%d %H:%M") 

        if distance <= FULL:
            waring_full()
            status.append(f"🚨 {trash_type} 已滿！請清理！現在時間 : {nowtime}")
            send_line(f"🚨 {trash_type} 已滿！請更換垃圾袋！")
            save_trash_full(trash_type)
            reset(trash_type) 

    return status




def reset(trash_type):
    print(f"🔍 監測 {trash_type} 是否清空...")
    target = None

    for key, value in trash_types.items():
        if value == trash_type:
            target = key
            break

    while True:
        time.sleep(5) 
        target_pin = ECHO_GPIO[int(target)-1]
        with DistanceSensor(echo=target_pin, trigger=TRIG) as sensor:
            time.sleep(0.1)
            distance = int(sensor.distance * 100)

        if distance > HEIGHT:
            print(f"✅ {trash_type} 已清空，系統重新啟動！")
            send_line(f"✅ {trash_type} 已清空，系統重新啟動！")
            return 
        



def send_line(message):
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINETOKEN}"}
    data = {"message": message}
    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        print("✅ 啟動LINE 訊息發送成功！")
    else:
        print(f"⚠️ Line錯誤碼: {response.status_code}，錯誤內容: {response.text}")



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





def clear_old_data():
    conn = sqlite3.connect("garbage_data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE trash_log SET times = 0")
    cursor.execute("UPDATE trash_full SET times = 0")
    
    conn.commit()
    conn.close()



try:
    while True:
        dist = distance() 
        if flag:
            if dist < 20  :
                flag=False
                detect_run()
                flag=True
            else:
                flag=False
                levels = garbage_levels() 
                for level in levels:
                    print(level)
                time.sleep(1) 
                flag=True

                
except KeyboardInterrupt:
    print("🛑 程式已停止")
    send_line(generate_report())
    clear_old_data()








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