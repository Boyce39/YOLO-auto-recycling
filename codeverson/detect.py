import cv2
from ultralytics import YOLO
from datetime import datetime
from gpiozero import DistanceSensor, Button ,Servo
import time
import sqlite3

def connect_db():
    return sqlite3.connect("garbage_data.db")


model = YOLO('bestv6.pt')


sensor = DistanceSensor(echo=23, trigger=24)
last_time = 0  


buttons = {
    "塑膠": Button(17, pull_up=True),
    "紙類": Button(27, pull_up=True),
    "金屬": Button(22, pull_up=True),
}

def open():
    servo = Servo(servo_GPIO, min_pulse_width=0.0005, max_pulse_width=0.0018)

    while True:
        print("自動程序啟動")

        servo.min()

        time.sleep(1)


        servo.max()

        time.sleep(1)

def save_data(category):
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO trash_log (category) VALUES (?)", (category,))
    
    conn.commit()
    conn.close()
    #print(f"✅ 已記錄分類: {category}")


def distance():
    return sensor.distance * 100 


def classification():
    print("⏳ 等待使用者分類（10 秒內）...否則丟往一般垃圾")

    start_time = time.time()
    
    while time.time() - start_time < 10:  
        for trash_type, button in buttons.items():
            if button.is_pressed:
                #print(f" 選擇 {trash_type} ")
                save_data(trash_type)  
                return trash_type  
            
        time.sleep(0.1)
    
    #print("⏳ AI 自動分類為『一般垃圾』")
    save_data("一般垃圾") 
    return "一般垃圾"


def run():
    cap = cv2.VideoCapture(0)  
    hold = 0.6  
    ret, frame = cap.read()

    print("""📸 拍照完成，正在執行 YOLO 偵測...
請稍後...
          """)

    results = model(frame)  
    detect = []
    low_confidence = False  
    
    for result in results[0].boxes:
        class_id = int(result.cls)  
        confidence = float(result.conf) 
        name = {0: '金屬', 1: '紙類', 2: '塑膠'}.get(class_id)#嘗試刪掉get,
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
        
        if dist < 10 and time.time() - last_time > 5:
            last_time = time.time()
            print("🔍 偵測物品掉落，開始檢測...\n")
            open()
            detected, low_confidence = run()
            
            #print(f"📢 檢測結果: {detected}")

            l=len(detected)

            if  l > 1 :
                if l==2 and detected.count('一般垃圾')==1:
                    detected.remove('一般垃圾')
                    final = detected[0]
                else:
                    #print("⚠️ 偵測到多個物品，請手動分類！")
                    final = classification()
                
            elif l ==0 :
                #print("⚠️ 未偵測到物品，請手動分類！")
                final = classification()
                
            else:
                final = detected[0]
                #print(f"✅ 物品分類結果：{final}")

            print(f"📦 最終分類結果：{final}")
            save_data(final)

        time.sleep(0.1) 

except KeyboardInterrupt:
    #print("🛑 程式已停止")
