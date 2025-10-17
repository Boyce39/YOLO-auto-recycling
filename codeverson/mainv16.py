import cv2
import os
from ultralytics import YOLO
from datetime import datetime
from gpiozero.tones import Tone
from gpiozero import DistanceSensor, Button, Servo, LED, TonalBuzzer, OutputDevice
import time
import requests
import sqlite3
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont, ImageDraw
import warnings
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
warnings.filterwarnings("ignore")

# 驗證 Google Drive
gauth = GoogleAuth()
gauth.LocalWebserverAuth() 
drive = GoogleDrive(gauth)
 = "/home/pi/Desktop/yolo_project/training_data"
DRIVE_FOLDER_ID = "你的Google Drive資料夾ID"

# 載入模型
model = YOLO('best-s.pt')
serial = i2c(port=1, address=0x3C)
oled = sh1106(serial)
last_time = 0   
TRIG = 5 
ECHO_GPIO = [6, 13, 16, 26]  
servo_GPIO = 19
HEIGHT = 50  
FULL = 20 
STEP_PIN = 14  # GPIO 14 → PU+ (步進訊號)
DIR_PIN = 15  # GPIO 15 → DR+ (方向控制)

serial = i2c(port=1, address=0x3C)
device = sh1106(serial, framebuffer="diff_to_previous", persist=True)
font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font = ImageFont.truetype(font_path, 15)
LINETOKEN = "naobDbheaBWNXenoF04pMkG7iwyBqQXhRc1SdDalm89"

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


def move(trash):
    M=8900
    P=6100
    Pl=3800
    g=1700
    step = OutputDevice(STEP_PIN)  # 步進訊號
    direction = OutputDevice(DIR_PIN)  # 方向控制
    steps = 8900
    speed = 0.00025
    if trash == "塑膠類":
        direction.value = False
        steps = Pl
        for _ in range(steps):
            step.on()
            time.sleep(speed)  
            step.off()
            time.sleep(speed)
        time.sleep(1)
        push()
        direction.value = True
        time.sleep(1)
        for _ in range(steps):
            step.on()
            time.sleep(speed)  
            step.off()
            time.sleep(speed)
    elif trash == "紙類":
        steps = P
        for _ in range(steps):
            step.on()
            time.sleep(speed)  
            step.off()
            time.sleep(speed)
        time.sleep(1)
        push()
        direction.value = True
        time.sleep(1)
        for _ in range(steps):
            step.on()
            time.sleep(speed)  
            step.off()
            time.sleep(speed)
    elif trash == "金屬類":
        steps = M
        for _ in range(steps):
            step.on()
            time.sleep(speed)  
            step.off()
            time.sleep(speed)
        time.sleep(1)
        push()
        direction.value = True
        time.sleep(1)
        for _ in range(steps):
            step.on()
            time.sleep(speed)  
            step.off()
            time.sleep(speed)
    elif trash == "一般垃圾":
        steps = g
        for _ in range(steps):
            step.on()
            time.sleep(speed)  
            step.off()
            time.sleep(speed)
        time.sleep(1)
        push()
        direction.value = True
        time.sleep(1)
        for _ in range(steps):
            step.on()
            time.sleep(speed)  
            step.off()
            time.sleep(speed)


def push():
    LOCK_PIN = 25  # GPIO 25 控制繼電器
    lock = OutputDevice(LOCK_PIN, active_high=False, initial_value=False)  # 低電平觸發
    lock.on()
    lock.off()
    time.sleep(1) 


def text_display(message):
    with canvas(device) as draw:
        draw.text((0, 0), message, font=font, fill="white")


def waring_choose():
    buzzer = TonalBuzzer(21)
    for _ in range(2):  
        buzzer.play(Tone(880)) 
        time.sleep(0.3)  
        buzzer.stop()
        time.sleep(0.2) 
    buzzer.stop()
    buzzer.close()


def waring_full():
    buzzer = TonalBuzzer(21)
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
    text_display("\n    開始檢測...")
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
    cursor.execute("UPDATE trash_log SET times = times + 1 WHERE category = ?", (category,))
    conn.commit()
    conn.close()


def save_trash_full(bin_type):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE trash_full SET times = times + 1 WHERE bin_type = ?", (bin_type,))
    conn.commit()
    conn.close()


def distance():
    sensor = DistanceSensor(echo=23, trigger=24)
    x=sensor.distance * 100 
    return x


def classification(port):
    waring_choose()
    print(f"⏳{port} 等待使用者分類（10 秒內）...否則丟往一般垃圾")
    text_display(f"{port}\n10秒內請按壓按鈕\n否則丟往一般垃圾")
    start_time = time.time()
    while time.time() - start_time < 10:  
        for trash_type, button in buttons.items():
            if button.is_pressed:
                return trash_type  
        time.sleep(0.1)
    return "一般垃圾"


# 修改：回傳影像、分類列表及詳細偵測資訊（包含 bbox 與信心值）
def run():
    open_door()
    ledpin = 18
    led = LED(ledpin)
    led.on()
    time.sleep(1)
    cap = cv2.VideoCapture(0)  
    hold = 0.6  
    ret, frame = cap.read()
    led.off()
    results = model(frame)  
    detect = []
    detection = []
    
    for result in results[0].boxes:
        class_id = int(result.cls)  
        confidence = float(result.conf) 
        class_name = {0: '金屬類', 1: '紙類', 2: '塑膠類'}
        
        name = {0: '金屬類', 1: '紙類', 2: '塑膠類'}.get(class_id)
        final = name if confidence >= hold else '一般垃圾'
        detect.append(final)

        bbox = result.xyxy[0].tolist()
        detection.append({"class_name": class_name, "confidence": confidence, "bbox": bbox})
    
    img = results[0].plot()  
    nowtime = datetime.now().strftime("%Y%m%d_%H%M%S") 
    save_img = f'/home/pi/Desktop/yolo_project/run_img/偵測_{nowtime}.jpg'
    cv2.imwrite(save_img, img)  
    cap.release()
    cv2.destroyAllWindows()  
    os.system("python3 music.py &")
    return frame, detect, detection


# 修改：在 detect_run 中，當無偵測結果時不儲存訓練資料，
# 且當需手動分類時只保留最終選擇類別所對應的 bbox 資料
def detect_run():
    os.system("python3 startsong.py &") 
    print("🔍 偵測物品掉落，開始檢測...\n")
    frame, detected, det_info = run()
    only = True
    l = len(detected)
    print(detected)
    
    # 若沒有偵測到任何物件，則呼叫手動分類，但不進行訓練資料儲存
    if l == 0:
        final = classification('無偵測到垃圾')
        print("無偵測結果，跳過儲存訓練資料")
    else:
        generally_count = detected.count('一般垃圾')
        if l == 2 and generally_count == 1:
            detected.remove('一般垃圾')
            final = detected[0]
        elif l > 2:
            if '一般垃圾' in detected:
                detected = [d for d in detected if d != '一般垃圾']
            l = len(detected)
            if l > 1:
                for i in range(1, l):
                    if detected[i-1] != detected[i]:
                        only = False
                        break          
            if only:
                final = detected[0]
            else:
                print('檢測失敗\n請按壓按鈕分類')
                final = classification('檢測失敗')
        elif '一般垃圾' in detected:
            print('檢測到一般垃圾如果偵測錯誤請按壓按鈕分類')
            final = classification('檢測到一般垃圾')
        else:
            final = detected[0]
        
        # 僅在有偵測結果的情況下儲存訓練資料（只儲存與 final 相符的 bbox）
        save_training_data(frame, det_info, final)
        save_data(final)
    
    os.system("python3 endsong.py &") 
    text_display(f"分類結果：\n       {final}")
    print(f"📦 最終分類結果：{final}")
    move(final)

def save_training_data(image, detection, final_class):
    """
    儲存訓練資料：
    若分類為「一般垃圾」，僅儲存影像；
    否則，儲存影像及相對應的標註 (bbox) 資料（只保留與最終選擇類別相符的 bbox）。
    """

    # 如果 detection_info 為空，則不儲存任何資料
    if not detection:
        print("無偵測到任何 bbox，故不儲存訓練資料")
        return
    
    if final_class == "一般垃圾":
        folder_path = "./general/"
        os.makedirs(folder_path, exist_ok=True)
        nowtime = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_file = os.path.join(folder_path, f"{nowtime}.jpg")
        cv2.imwrite(img_file, image)
    else:
        folder_path = "./auto/train/images/"
        label_folder = "./auto/train/labels/"
        os.makedirs(folder_path, exist_ok=True)
        os.makedirs(label_folder, exist_ok=True)
        nowtime = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_file = os.path.join(folder_path, f"{nowtime}.jpg")
        cv2.imwrite(img_file, image)
        # 只保留與最終分類相符的 bbox
        bboxes = [d["bbox"] for d in detection if d["class_name"] == final_class]
        if bboxes:
            txt_file = os.path.join(label_folder, f"{nowtime}.txt")
            h, w, _ = image.shape
            with open(txt_file, "w") as f:
                for bbox in bboxes:
                    x_min, y_min, x_max, y_max = bbox
                    x_center = ((x_min + x_max) / 2) / w
                    y_center = ((y_min + y_max) / 2) / h
                    width = (x_max - x_min) / w
                    height = (y_max - y_min) / h
                    class_mapping = {'金屬類': 0, '紙類': 1, '塑膠類': 2}
                    class_id = class_mapping.get(final_class, -1)
                    if class_id == -1:
                        continue
                    f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
   #print(f"✅ {final_class} 數據已存入: {img_file}")

def garbage_levels():
    status = []
    for i, echo_pin in enumerate(ECHO_GPIO):
        with DistanceSensor(echo=echo_pin, trigger=TRIG) as sensor:
            time.sleep(0.1)  
            distance_val = int(sensor.distance * 100)
            #print(distance_val)
        trash_type = trash_types.get(str(i+1), f"垃圾桶 {i+1}")
        nowtime = datetime.now().strftime("%Y-%m-%d %H:%M") 
        if distance_val <= FULL:
            waring_full()
            send_line(f"\n🚨 {trash_type} 已滿！請更換垃圾袋！\n現在時間 : {nowtime}")
            save_trash_full(trash_type)
            reset(trash_type)
    return 


def reset(trash_type):
    print(f"🔍 監測 {trash_type} 是否清空...")
    text_display(f"{trash_type}已滿!\n請盡快清理")
    target = None
    for key, value in trash_types.items():
        if value == trash_type:
            target = key
            break
    while True:
        time.sleep(0.1) 
        target_pin = ECHO_GPIO[int(target)-1]
        with DistanceSensor(echo=target_pin, trigger=TRIG) as sensor:
            time.sleep(0.1)
            distance_val = int(sensor.distance * 100)
        if distance_val > HEIGHT:
            nowtime = datetime.now().strftime("%Y-%m-%d %H:%M") 
            print(f"✅ {trash_type} 已清空，系統重新啟動！")
            text_display(f"{trash_type} 已清空\n系統重新啟動！")
            send_line(f"\n✅ {trash_type} 已清空，系統重新啟動！\n現在時間 : {nowtime}")
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
        message_trash = "\n📊 本次運行的垃圾分類數據：\n" + "❌ 本次運行沒有記錄到任何垃圾分類數據。\n"
    message_full = "\n🗑 本次運行的垃圾桶滿溢狀態：\n"
    has_full_data = False 
    for row in full_data:
        bin_type, count = row
        message_full += f"{bin_type}: {count} 次\n"
        if count > 0:
            has_full_data = True
    if not has_full_data:
        message_full = "\n🗑 本次運行的垃圾桶滿溢狀態：\n" + "✅ 本次沒有垃圾桶滿溢記錄，狀況良好。\n"
    return message_trash + message_full


def clear_old_data():
    conn = sqlite3.connect("garbage_data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE trash_log SET times = 0")
    cursor.execute("UPDATE trash_full SET times = 0")
    conn.commit()
    conn.close()



# 新增：觸發 YOLO 增量訓練
def trigger_training():
    print("🔄 開始 YOLO 增量訓練...")
    train_command = 'yolo task=detect mode=train model=/home/pi/Desktop/yolo_project/best.pt data=/home/pi/Desktop/yolo_project/auto/data.yaml epochs=100 imgsz=640'
    print(f"📌 執行 YOLO 訓練指令：\n{train_command}")
    try:
        os.system(train_command)
        update_model()
    except Exception as e:
        print(f" YOLO 訓練失敗：{e}")


# 新增：更新最新模型
def update_model():
    src_model = "./runs/detect/train/weights/best.pt"
    dst_model = "./bestv6.pt"
    if os.path.exists(src_model):
        os.system(f'cp "{src_model}" "{dst_model}"')
        print("✅ 新 YOLO 模型已更新！")
    else:
        print("❌ 模型訓練失敗，未找到 `best.pt`，請檢查 YOLO 訓練過程")


try:
    print("\n系統啟動中...")
    text_display("系統啟動中...")
    while True:
        text_display("  系統正常\n  請投入垃圾...")
        dist = distance()
        print(dist)
       # print(dist)

        if dist < 20:
            detect_run()
            text_display("  系統正常\n  請投入垃圾...")
        else:
            garbage_levels()
except KeyboardInterrupt:
    print("🛑 程式已停止")
    text_display("\n程式已停止...")
    # 結束時觸發增量訓練
    #trigger_training()
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
    
# init_db()
