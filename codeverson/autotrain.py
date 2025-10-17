import cv2
import os
import time
import shutil
import subprocess
from ultralytics import YOLO
from datetime import datetime

# 🚀 載入最新 YOLO 模型
model_path = "best.pt"
model = YOLO(model_path)
print(f"✅ 已加載最新 YOLO 模型：{model_path}")

# 📌 定義垃圾分類對應的 Class ID
trash_classes = {
    "Metal": 0,
    "paper": 1,
    "plastic": 2
}

# 📌 模擬攝影機拍攝（用本地圖片代替攝影機拍攝）
def capture_image():
    """模擬攝影機拍攝，從本地圖片資料夾中讀取影像"""
    img_folder = "./test_images/"
    images = [os.path.join(img_folder, f) for f in os.listdir(img_folder) if f.endswith(".jpg")]
    
    if not images:
        print("❌ 沒有測試圖片，請在 `test_images/` 資料夾中放入測試圖片")
        return None, None
    
    img_path = images[0]  # 取第一張圖片測試
    frame = cv2.imread(img_path)
    return frame, img_path

# 📌 偵測垃圾分類
def run(frame):
    """執行 YOLO 偵測垃圾分類"""
    results = model(frame)
    detected = []

    for result in results[0].boxes:
        class_id = int(result.cls)
        confidence = float(result.conf)
        bbox = result.xyxy[0].tolist()

        name = {0: 'Metal', 1: 'paper', 2: 'plastic'}.get(class_id, "未知類別")
        final = name if confidence >= 0.6 else '一般垃圾'

        detected.append({
            "class_name": final,
            "confidence": confidence,
            "bbox": bbox
        })

    return detected

# 📌 使用 input() 替代按鈕輸入
def manual_classification():
    """當 YOLO 分類不準時，讓使用者手動輸入分類"""
    print("🛑 請輸入垃圾類別（Metal / paper / plastic / 一般垃圾）：")
    while True:
        user_input = input("> ").strip()
        if user_input in ["Metal", "paper", "plastic", "一般垃圾"]:
            return user_input
        else:
            print("❌ 輸入錯誤，請輸入：Metal / paper / plastic / 一般垃圾")

# 📌 偵測流程（完整 `detect_run()`）
def detect_run():
    last_time = time.time()
    print("🔍 偵測物品掉落，開始檢測...\n")

    frame, img_path = capture_image()
    if frame is None:
        return

    detected = run(frame)
    only = True  
    l = len(detected)

    # 計算各種垃圾類型的數量
    generally_count = sum(1 for d in detected if d["class_name"] == '一般垃圾')

    # **📌 確保 `final_class` 為單一分類**
    if l == 2 and generally_count == 1:
        detected = [d for d in detected if d["class_name"] != "一般垃圾"]
        final_class = detected[0]["class_name"]

    elif l > 2:
        detected = [d for d in detected if d["class_name"] != "一般垃圾"]
        l = len(detected)
        if l > 1:
            for i in range(1, l):
                if detected[i-1]["class_name"] != detected[i]["class_name"]:
                    only = False
                    break          
        if only:
            final_class = detected[0]["class_name"]
        else:
            print('❌ 檢測失敗，請輸入垃圾類別')
            final_class = manual_classification()

    elif "一般垃圾" in [d["class_name"] for d in detected]:
        print('⚠️ 檢測到一般垃圾，如偵測錯誤請輸入正確分類')
        final_class = manual_classification()

    elif l == 0:
        final_class = manual_classification()

    else:
        final_class = detected[0]["class_name"]

    print(f"📦 最終分類結果：{final_class}")

    # 📌 儲存分類結果
    save_training_data(frame, detected, final_class)

    # 📌 🔥 在 `detect_run()` 結束後，開始 YOLO 訓練
    print("🛑 檢測完成，等待程式關閉後訓練 YOLO...")



# 📌 儲存數據
def save_training_data(image, detected, final_class):
    """只儲存與 final_class 相符的 bbox，確保標註正確"""
    
    if final_class == "一般垃圾":
        folder_path = "./dataset/images/general/"
    else:
        folder_path = "./dataset/images/train/"
        label_folder = "./dataset/labels/train/"
        os.makedirs(label_folder, exist_ok=True)

    os.makedirs(folder_path, exist_ok=True)

    nowtime = datetime.now().strftime("%Y%m%d_%H%M%S")
    img_file = os.path.join(folder_path, f"{nowtime}.jpg")
    cv2.imwrite(img_file, image)

    # **📌 只存與 final_class 相符的 bbox**
    filtered_bboxes = [d["bbox"] for d in detected if d["class_name"] == final_class]

    # **📌 只有非「一般垃圾」才存標註**
    if final_class != "一般垃圾" and len(filtered_bboxes) > 0:
        txt_file = os.path.join(label_folder, f"{nowtime}.txt")

        h, w, _ = image.shape
        with open(txt_file, "w") as f:
            for bbox in filtered_bboxes:
                x_min, y_min, x_max, y_max = bbox
                x_center = ((x_min + x_max) / 2) / w
                y_center = ((y_min + y_max) / 2) / h
                width = (x_max - x_min) / w
                height = (y_max - y_min) / h

                class_id = trash_classes.get(final_class, -1)
                if class_id == -1:
                    continue
                f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

    print(f"✅ {final_class} 數據已存入: {img_file}")

def trigger_training():
    """程式結束後，立即開始 YOLO 訓練"""
    print("🔄 開始 YOLO 訓練...")

    train_command = (
        'yolo task=detect mode=train '
        'model=r"C:\Users\Cyborg 15\Desktop\模型訓練\best.pt'
        'data=data.yaml '
        'epochs=100 imgsz=640' )

    print(f"📌 執行 YOLO 訓練指令：\n{train_command}")

    try:
        os.system(train_command)  # 使用 os.system() 執行 YOLO 訓練
        update_model()
    except Exception as e:
        print(f"❌ YOLO 訓練失敗：{e}")



def update_model():
    """當 YOLO 訓練完成後，自動更新最新模型"""
    src_model = "./runs/detect/train/weights/best.pt"
    dst_model = "./best.pt"

    if os.path.exists(src_model):
        os.system(f'copy "{src_model}" "{dst_model}"')  # 使用 os.system() 來複製文件
        print("✅ 新 YOLO 模型已更新！")
    else:
        print("❌ 模型訓練失敗，未找到 `best.pt`，請檢查 YOLO 訓練過程")



# 📌 讓程式在關閉時訓練 YOLO
try:
    while True:
        if input():
            detect_run()
except KeyboardInterrupt:
    print("\n🛑 偵測過程中斷，開始訓練 YOLO...")
    trigger_training()
