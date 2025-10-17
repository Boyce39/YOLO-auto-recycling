import cv2
from ultralytics import YOLO
from datetime import datetime
from gpiozero import DistanceSensor, Button
import time
import sqlite3

def connect_db():
    return sqlite3.connect("garbage_data.db")

# 🔹 初始化 YOLO 模型
model = YOLO('bestv6.pt')

# 🔹 超音波感測器
sensor = DistanceSensor(echo=23, trigger=24)
last_time = 0  

# 🔹 按鈕（手動分類）
buttons = {
    "塑膠": Button(17, pull_up=True),
    "紙類": Button(27, pull_up=True),
    "金屬": Button(22, pull_up=True),
}


# 🔹 記錄垃圾分類數據
def save_data(category):
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO trash_log (category) VALUES (?)", (category,))
    
    conn.commit()
    conn.close()
    print(f"✅ 已記錄分類: {category}")

# 🔹 取得距離（確認是否有物品掉落）
def distance():
    return sensor.distance * 100 

# 🔹 手動分類（等待使用者按按鈕）
def classification():
    print("⏳ 等待使用者分類（10 秒內）...")
    start_time = time.time()
    
    while time.time() - start_time < 10:  # 限時 10 秒
        for trash_type, button in buttons.items():
            if button.is_pressed:
                print(f"✅ 選擇 {trash_type} ")
                save_data(trash_type)  # ✅ 記錄分類數據
                return trash_type  # 返回使用者選擇的分類
        time.sleep(0.1)
    
    print("⏳ AI 自動分類為『一般垃圾』")
    save_data("一般垃圾")  # ✅ 記錄分類數據
    return "一般垃圾"

# 🔹 物件偵測函數
def run():
    cap = cv2.VideoCapture(0)  
    hold = 0.6  
    ret, frame = cap.read()

    if not ret:
        print("⚠️ 攝影機無法捕獲影像，請檢查連接！")
        cap.release()
        return []

    print("""📸 拍照完成，正在執行 YOLO 偵測...
請稍後...
          """)

    results = model(frame)  
    detect = []
    low_confidence = False  # 紀錄是否有低置信度的物品
    
    for result in results[0].boxes:
        class_id = int(result.cls)  
        confidence = float(result.conf) 
        name = {0: '金屬', 1: '紙類', 2: '塑膠'}.get(class_id, '一般垃圾')
        final = name if confidence >= hold else '一般垃圾'

        if confidence < hold:
            low_confidence = True  # 若有低置信度物品，啟動手動分類機制
        
        detect.append(final)

    # 儲存 YOLO 偵測影像
    img = results[0].plot()  
    nowtime = datetime.now().strftime("%Y%m%d_%H%M%S") 
    save_img = f'/home/pi/Desktop/yolo_project/run_img/偵測_{nowtime}.jpg'
    cv2.imwrite(save_img, img)  
    cap.release()
    cv2.destroyAllWindows()  

    return detect, low_confidence  

# 🔹 主要執行迴圈
try:
    while True:
        dist = distance()  
        
        if dist < 10 and time.time() - last_time > 5:
            last_time = time.time()
            print("🔍 偵測物品掉落，開始檢測...")
            detected, low_confidence = run()
            
            print(f"📢 檢測結果: {detected}")
            l=len(detected)
            if  l > 1 :
                if l==2 and detected.count('一般垃圾')==1:
                    detected.remove('一般垃圾')
                    final = detected[0]
                else:
                    print("⚠️ 偵測到多個物品，請手動分類！")
                    final = classification()
                
            elif l ==0 :
                print("⚠️ 未偵測到物品，請手動分類！")
                final = classification()
                
            else:
                final = detected[0]
                print(f"✅ 物品分類結果：{final}")

            print(f"📦 最終分類結果：{final}")
            save_data(final)

        time.sleep(0.1)  

except KeyboardInterrupt:
    print("🛑 程式已停止")
