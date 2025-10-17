import cv2
from ultralytics import YOLO
from datetime import datetime
from gpiozero import DistanceSensor
from gpiozero import Button
import time
import subprocess  

sensor_process = subprocess.Popen(["python3", "sensor_LINEv2.py"])

model = YOLO('bestv6.pt')

sensor = DistanceSensor(echo=24, trigger=23)

last_time = 0  

def distance():
    return sensor.distance * 100 

def run():
    cap = cv2.VideoCapture(0)  
    confidence_threshold = 0.6  
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

    for result in results[0].boxes:
        class_id = int(result.cls)  
        confidence = float(result.conf) 
        name = {0: '金屬', 1: '紙類', 2: '塑膠'}.get(class_id, '一般垃圾')
        final_class = name if confidence >= confidence_threshold else '一般垃圾'
        detect.append(final_class)

    img = results[0].plot()  
    nowtime = datetime.now().strftime("%Y%m%d_%H%M%S") 
    save_img = f'/home/pi/Desktop/yolo_project/run_img/偵測_{nowtime}.jpg'
    cv2.imwrite(save_img, img)  
    cap.release()
    cv2.destroyAllWindows()  
    #print(f"✅ 偵測結果已儲存在 {save_img}")
    return detect  


try:
    while True:
        dist = distance()  
        if dist < 10 and time.time() - last_time > 5:
            last_time = time.time()
            print("🔍偵測物品掉落，開始檢測...")
            detected_classes = run()
            print(f"📢 檢測結果: {detected_classes}")
            #滑軌分類
        time.sleep(0.1)

except KeyboardInterrupt:
    print("🛑 程式已停止")
    sensor_process.terminate() 
    #print("🛑 已關閉 `sensor_LINE.py`")
