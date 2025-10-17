import cv2
from ultralytics import YOLO
from datetime import datetime
from gpiozero import DistanceSensor, Button ,Servo,LED
import time
import sqlite3
import warnings
warnings.filterwarnings("ignore")

model = YOLO('bestv6.pt')
sensor = DistanceSensor(echo=23, trigger=24)
last_time = 0   
flag=True

def connect_db():
    return sqlite3.connect("garbage_data.db")

buttons = {
    "塑膠": Button(17, pull_up=True),
    "紙類": Button(27, pull_up=True),
    "金屬": Button(22, pull_up=True),
}

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


def distance():
    return sensor.distance * 100 

def classification():
    print("⏳ 等待使用者分類（10 秒內）...否則丟往一般垃圾")

    start_time = time.time()

    while time.time() - start_time < 10:  
        for trash_type, button in buttons.items():
            if button.is_pressed:
                return trash_type  
            
        time.sleep(0.1)

    return "一般垃圾"


def run():
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
    low_confidence = False  
    
    for result in results[0].boxes:
        class_id = int(result.cls)  
        confidence = float(result.conf) 
        name = {0: '金屬', 1: '紙類', 2: '塑膠'}.get(class_id)
        final = name if confidence >= hold else '一般垃圾'

        if confidence < hold:
            low_confidence = True  
        
        detect.append(final)

    
    img = results[0].plot()  
    nowtime = datetime.now().strftime("%Y%m%d_%H%M%S") 
    save_img = f'/home/pi/Desktop/yolo_project/run_img/偵測_{nowtime}.jpg'

    cv2.imwrite(save_img, img)  

    cap.release()

    cv2.destroyAllWindows()  

    return detect, low_confidence  


try:
    while True:
        dist = distance() 
        if flag:
            if dist < 20  :
                flag=False
                last_time = time.time()
                print("🔍 偵測物品掉落，開始檢測...\n")
                open_door()
                detected, low_confidence = run()
                l=len(detected)
                if  l > 1 :
                    if l==2 and detected.count('一般垃圾')==1:
                        detected.remove('一般垃圾')
                        final = detected[0]
                    else:
                        final = classification()
                elif l ==0 :
                    final = classification()
                else:
                    final = detected[0]
                save_data(final)
                print(f"📦 最終分類結果：{final}")   
                flag=True
            time.sleep(5) 
except KeyboardInterrupt:
    print("stop detect")

