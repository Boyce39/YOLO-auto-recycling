import cv2
from ultralytics import YOLO
from datetime import datetime

model = YOLO('bestv5.pt') #我的模型可更改

def run():
    cap = cv2.VideoCapture(0)
    x=0.6 #可信度臨界值
    ret, frame = cap.read()
    print("拍照完成")
    results = model(frame)  # fram =>NumPy 格式的影像數據
    detect = []
    for result in results[0].boxes:         #results[0] 是二為數據[0]裡面的資料，.boxes是我要取檢測後的資訊
        class_id = int(result.cls)          # .cls為類別
        confidence = float(result.conf)     # .conf為檢測後的準確度
        name={0: '金屬', 1: '紙類', 2: '塑膠'}.get(class_id, '一般垃圾')       #建立字典因為我只有訓練三個類別，所以要在把一般垃圾加上去
        final_class = name if confidence >= x else '一般垃圾'
        detect.append(final_class)
    
    img=results[0].plot()   #繪製已標註圖片
    nowtime = datetime.now().strftime("%Y%m%d_%H%M%S")  # 格式化當前時間
    save_img = f'runs/detect/偵測{nowtime}.jpg'  
    cv2.imwrite(save_img, img)  # 保存圖片
    return detect

    cap.release()
while True:
    if input():
        print("檢測到:",*run())
        break

