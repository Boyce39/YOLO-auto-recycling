import cv2
from ultralytics import YOLO
from datetime import datetime
from gpiozero import DistanceSensor
import time

model = YOLO('bestv6.pt')  # YOLO 模型名稱，可更改

# 超音波感測器初始化
TRIG = 23  
ECHO = 24  
sensor = DistanceSensor(echo=ECHO, trigger=TRIG)

# 記錄最後偵測時間，避免連續觸發
last_detect_time = 0  

# 取得超音波感測器測得的距離（公分）
def distance():
    return sensor.distance * 100  # 轉換為公分

# 物件偵測函數
def run():
    cap = cv2.VideoCapture(0)  # 開啟攝影機
    confidence_threshold = 0.6  # 設定可信度門檻值
    ret, frame = cap.read()

    if not ret:
        print("攝影機無法捕獲影像，請檢查連接！")
        cap.release()
        return []

    print("拍照完成，正在執行 YOLO 偵測...")

    # 執行 YOLO 偵測
    results = model(frame)  
    detect = []

    for result in results[0].boxes:
        class_id = int(result.cls)  # 取得類別 ID
        confidence = float(result.conf)  # 取得置信度

        # 透過字典轉換類別名稱，若不在範圍內則為 "一般垃圾"
        name = {0: '金屬', 1: '紙類', 2: '塑膠'}.get(class_id, '一般垃圾')
        final_class = name if confidence >= confidence_threshold else '一般垃圾'
        detect.append(final_class)

    # 生成標註影像並保存
    img = results[0].plot()  # YOLO 繪製標註
    nowtime = datetime.now().strftime("%Y%m%d_%H%M%S")  # 取得時間
    save_img = f'/home/pi/Desktop/yolo_project/run_img/偵測_{nowtime}.jpg'
    cv2.imwrite(save_img, img)  # 保存圖片

    cap.release()
    cv2.destroyAllWindows()  # 釋放 OpenCV 資源
    print(f"偵測結果已儲存在 {save_img}")
    return detect  # 返回偵測結果

# 主要執行迴圈
try:
    while True:
        disti = distance()  # 取得感測距離
        distf=disti
        if disti != distf:
            last_detect_time = time.time()
            print("偵測物品掉落，開始檢測...")
            detected_classes = run()
            print(f"檢測結果: {detected_classes}")

        time.sleep(0.1)  

except :
    print("程式已停止")
