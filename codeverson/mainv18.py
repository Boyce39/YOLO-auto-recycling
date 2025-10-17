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
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

warnings.filterwarnings("ignore")

# ------------------ Google Drive 設定 ------------------
SERVICE_ACCOUNT_FILE = "/home/pi/Desktop/yolo_project/service_account.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build("drive", "v3", credentials=creds)
GOOGLE_DRIVE_FOLDER_ID = "12jyXGfuKG1yNTZsOfe4-mVz9bRB4S32v"

# ------------------ 訓練資料夾設定 ------------------
TRAIN_FOLDER = "/home/pi/Desktop/yolo_project/auto/train"
LABELS_FOLDER = "/home/pi/Desktop/yolo_project/auto/train/labels"
IMAGES_FOLDER = "/home/pi/Desktop/yolo_project/auto/train/images"

# ------------------ 載入模型與其他設備設定 ------------------
model = YOLO('bestv6-s歐剉.pt')
serial = i2c(port=1, address=0x3C)
oled = sh1106(serial)
last_time = 0   
TRIG = 5 
ECHO_GPIO = [6, 13, 16, 26]  
servo_GPIO = 19
FULL = 25
STEP_PIN = 15  # GPIO 14 → PU+ (步進訊號)
DIR_PIN = 14   # GPIO 15 → DR+ (方向控制)

serial = i2c(port=1, address=0x3C)
device = sh1106(serial, framebuffer="diff_to_previous", persist=True)
font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font = ImageFont.truetype(font_path, 15)
LINETOKEN = "naobDbheaBWNXenoF04pMkG7iwyBqXhRc1SdDalm89"

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

# ------------------ 標準化函式 ------------------
def standardize_label(label):
    mapping = {
        "紙類": "紙類",
        "塑膠": "塑膠類",
        "塑膠類": "塑膠類",
        "金屬": "金屬類",
        "金屬類": "金屬類",
        "一般垃圾": "一般垃圾"
    }
    return mapping.get(label, label)

# ------------------ 事件記錄函式 ------------------
def log_trash_event(category):
    category = standardize_label(category)
    conn = sqlite3.connect("garbage_data.db")
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO trash_events (timestamp, category) VALUES (?, ?)", (now, category))
    conn.commit()
    conn.close()

def log_bin_event(bin_type, event_type):
    conn = sqlite3.connect("garbage_data.db")
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO bin_events (timestamp, bin_type, event_type) VALUES (?, ?, ?)", (now, bin_type, event_type))
    conn.commit()
    conn.close()

# ------------------ 儲存資料函式 ------------------
def save_data(category):
    conn = sqlite3.connect("garbage_data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE trash_log SET times = times + 1 WHERE category = ?", (category,))
    conn.commit()
    conn.close()

def save_trash_full(bin_type):
    conn = sqlite3.connect("garbage_data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE trash_full SET times = times + 1 WHERE bin_type = ?", (bin_type,))
    conn.commit()
    conn.close()

# ------------------ 移動與控制相關 ------------------
def move(trash):
    step = OutputDevice(STEP_PIN)
    direction = OutputDevice(DIR_PIN)
    SPEED = 0.00025
    STEPS_MAP = {
        "塑膠類": 4350,
        "紙類": 6800,
        "金屬類": 8900,
        "一般垃圾": 2000
    }
    steps = STEPS_MAP.get(trash, 0)
    direction.value = False
    for _ in range(steps):
        step.on()
        time.sleep(SPEED)  
        step.off()
        time.sleep(SPEED)
    direction.value = True
    push()
    time.sleep(0.5)
    for _ in range(steps):
        step.on()
        time.sleep(SPEED)  
        step.off()
        time.sleep(SPEED)

def push():
    LOCK_PIN = 25
    lock = OutputDevice(LOCK_PIN, active_high=False, initial_value=False)
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

# ------------------ 資料庫連線與固定表格建立 ------------------
def connect_db():
    return sqlite3.connect("garbage_data.db")

def init_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trash_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT UNIQUE,
        times INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trash_full (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bin_type TEXT UNIQUE,
        times INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trash_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        category TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bin_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        bin_type TEXT,
        event_type TEXT
    )
    """)
    # 插入預設垃圾分類（僅一次）
    default_trash_types = ["紙類", "塑膠類", "金屬類", "一般垃圾"]
    for category in default_trash_types:
        cursor.execute("INSERT OR IGNORE INTO trash_log (category, times) VALUES (?, 0)", (category,))
    default_bins = ["紙類回收桶", "塑膠回收桶", "金屬回收桶", "一般垃圾桶"]
    for bin_type in default_bins:
        cursor.execute("INSERT OR IGNORE INTO trash_full (bin_type, times) VALUES (?, 0)", (bin_type,))
    conn.commit()
    conn.close()

init_db()

# ------------------ 開門與分類 ------------------
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

# ------------------ 定義 distance 函式 ------------------
def distance():
    sensor = DistanceSensor(echo=23, trigger=24)
    return sensor.distance * 100

# ------------------ 偵測與分類流程 ------------------
def run():
    open_door()
    led = LED(18)
    led.on()
    time.sleep(1)
    
    cap = cv2.VideoCapture(0)
    hold = 0.6  
    ret, frame = cap.read()
    led.off()
    
    results = model(frame)
    detect = []
    detection = []
    class_mapping = {0: '金屬類', 1: '紙類', 2: '塑膠類'}
    for result in results[0].boxes:
        class_id = int(result.cls)
        confidence = float(result.conf)
        class_name = class_mapping.get(class_id, "未知類別")
        final = class_name if confidence >= hold else '一般垃圾'
        detect.append(final)
        bbox = result.xyxy[0].tolist()
        detection.append({
            "class_name": class_name,
            "confidence": confidence,
            "bbox": bbox
        })
    nowtime = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_img = f'/home/pi/Desktop/yolo_project/run_img/偵測_{nowtime}.jpg'
    cv2.imwrite(save_img, results[0].plot())
    cap.release()
    cv2.destroyAllWindows()
    # 如果沒有 music.py，請註解此行或建立一個空的 music.py
    os.system("python3 music.py &")
    return frame, detect, detection

def detect_run():
    os.system("python3 startsong.py &")
    print("🔍 偵測物品掉落，開始檢測...\n")
    frame, detected, det_info = run()
    only = True
    l = len(detected)
    print("🧐 Debugging: detected =", detected)
    if detected is None:
        detected = []
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
    print(f"📦 最終分類結果：{final}")
    final = standardize_label(final)
    log_trash_event(final)
    save_training_data(frame, det_info, final)
    save_data(final)
    os.system("python3 endsong.py &")
    text_display(f"分類結果：\n       {final}")
    move(final)

def save_training_data(image, detection, final_class, manual_classification=False):
    if isinstance(final_class, list):
        final_class = final_class[0]
    print(f"🧐 Debugging: final_class = {final_class}, type = {type(final_class)}")
    if not detection:
        print("無偵測到任何 bbox，故不儲存訓練資料")
        return
    nowtime = datetime.now().strftime("%Y%m%d_%H%M%S")
    if final_class == "一般垃圾":
        folder_path = "./general/"
        os.makedirs(folder_path, exist_ok=True)
        img_file = os.path.join(folder_path, f"{nowtime}.jpg")
        cv2.imwrite(img_file, image)
        print(f"✅ {final_class} 數據已存入: {img_file} (但不標註)")
        return
    image_folder = "/home/pi/Desktop/yolo_project/auto/train/images"
    label_folder = "/home/pi/Desktop/yolo_project/auto/train/labels"
    os.makedirs(image_folder, exist_ok=True)
    os.makedirs(label_folder, exist_ok=True)
    img_file = os.path.join(image_folder, f"{nowtime}.jpg")
    cv2.imwrite(img_file, image)
    bboxes = [
        d["bbox"] for d in detection
        if isinstance(d["class_name"], str)
        and d["class_name"].strip() == final_class.strip()
        and (d["confidence"] >= 0.6 or manual_classification)
    ]
    if not bboxes:
        print(f"⚠無符合 {final_class} 的 bbox（未達置信度門檻 0.6），圖片已存，但不寫入標註。")
        return
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
            class_id = class_mapping.get(final_class.strip(), -1)
            if class_id == -1:
                print(f"⚠️ 未知類別 {final_class}，無法寫入標註。")
                continue
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
    print(f"✅ {final_class} 數據已存入: {img_file}，標註檔案: {txt_file}")

# ------------------ 垃圾桶狀態監測 ------------------
def garbage_levels():
    for i, echo_pin in enumerate(ECHO_GPIO):
        with DistanceSensor(echo=echo_pin, trigger=TRIG) as sensor:
            time.sleep(0.1)
            distance_val = int(sensor.distance * 100)
        trash_type = trash_types.get(str(i+1), f"垃圾桶 {i+1}")
        nowtime = datetime.now().strftime("%Y-%m-%d %H:%M")
        if distance_val <= FULL:
            waring_full()
            send_line(f"\n🚨 {trash_type} 已滿！請更換垃圾袋！\n現在時間 : {nowtime}")
            save_trash_full(trash_type)
            log_bin_event(trash_type, "full")
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
        if distance_val > FULL:
            nowtime = datetime.now().strftime("%Y-%m-%d %H:%M")
            print(f"✅ {trash_type} 已清空，系統重新啟動！")
            text_display(f"{trash_type} 已清空\n系統重新啟動！")
            send_line(f"\n✅ {trash_type} 已清空，系統重新啟動！\n現在時間 : {nowtime}")
            log_bin_event(trash_type, "clear")
            return

# ------------------ LINE 訊息發送 ------------------
def send_line(message):
    LINETOKEN = "naobDbheaBWNXenoF04pMkG7iwyBqQXhRc1SdDalm89"
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINETOKEN}"}
    data = {"message": message}
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        print("✅ 啟動LINE 訊息發送成功！")
    else:
        print(f"⚠️ Line錯誤碼: {response.status_code}，錯誤內容: {response.text}")

# ------------------ 資料統計與報告 ------------------
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

# ------------------ 修改清除資料函式 ------------------
# 清除表格中的所有資料，但保留表格結構
def clear_old_data():
    conn = sqlite3.connect("garbage_data.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trash_log")
    cursor.execute("DELETE FROM trash_full")
    cursor.execute("DELETE FROM trash_events")
    cursor.execute("DELETE FROM bin_events")
    conn.commit()
    conn.close()

# ------------------ Google Drive 上傳相關 ------------------
def create_drive_folder(folder_name, parent_folder_id):
    query = f"name = '{folder_name}' and '{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]
    else:
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id]
        }
        folder = drive_service.files().create(body=file_metadata, fields="id").execute()
        return folder["id"]

def upload_folder(local_folder, drive_parent_folder_id):
    folder_name = os.path.basename(local_folder)
    drive_folder_id = create_drive_folder(folder_name, drive_parent_folder_id)
    for root, dirs, files in os.walk(local_folder):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            file_metadata = {
                "name": file_name,
                "parents": [drive_folder_id]
            }
            mime_type = "image/jpeg" if file_name.endswith((".jpg", ".jpeg", ".png")) else "text/plain"
            try:
                media = MediaFileUpload(file_path, mimetype=mime_type)
                drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
                print(f"✅ 已上傳: {file_path}")
            except Exception as e:
                print(f"❌ 上傳失敗: {file_path}, 錯誤: {e}")

def upload_to_drive():
    try:
        label_files = os.listdir(LABELS_FOLDER)
        if len(label_files) >= 5:
            print(f" 偵測到 {len(label_files)} 個標註檔案，開始上傳")
            text_display("資料自動上傳中")
            upload_folder(IMAGES_FOLDER, GOOGLE_DRIVE_FOLDER_ID)
            upload_folder(LABELS_FOLDER, GOOGLE_DRIVE_FOLDER_ID)
            shutil.rmtree(IMAGES_FOLDER)
            shutil.rmtree(LABELS_FOLDER)
            os.makedirs(IMAGES_FOLDER)
            os.makedirs(LABELS_FOLDER)
            print("料夾已清空，等待新的訓練數據。")
        else:
            print(f"數據僅有 {len(label_files)} 個檔案，未達上傳條件，跳過")
    except KeyboardInterrupt:
        print(" 手動中斷，停止上傳...")

# ------------------ 圖表產生 (根據需求只產生5張圖表) ------------------
def generate_charts():
    font_path = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
    font_prop = fm.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = font_prop.get_name()
    plt.rcParams['axes.unicode_minus'] = False
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_folder = f"/home/pi/Desktop/yolo_project/data/{timestamp}"
    os.makedirs(output_folder, exist_ok=True)
    print(f"建立圖表資料夾: {output_folder}")
    conn = sqlite3.connect("garbage_data.db")
    
    # 1. 不同時段丟入垃圾統計 (折線圖)
    try:
        df_events = pd.read_sql_query("SELECT timestamp, category FROM trash_events", conn)
        df_events['timestamp'] = pd.to_datetime(df_events['timestamp'])
        df_events['hour'] = df_events['timestamp'].dt.hour
        events_by_hour = df_events.groupby('hour').size().reset_index(name='count')
        events_by_hour = events_by_hour.sort_values('hour')
        plt.figure(figsize=(10, 6))
        plt.plot(events_by_hour['hour'], events_by_hour['count'], marker='o')
        plt.title("不同時段丟入垃圾統計", fontproperties=font_prop)
        plt.xlabel("時段（小時）", fontproperties=font_prop)
        plt.ylabel("垃圾丟入次數", fontproperties=font_prop)
        plt.xticks(fontproperties=font_prop)
        plt.yticks(fontproperties=font_prop)
        plt.tight_layout()
        chart1_path = os.path.join(output_folder, "不同時段丟入垃圾統計.png")
        plt.savefig(chart1_path)
        plt.close()
        print(f"圖表已儲存：{chart1_path}")
    except Exception as e:
        print("產生不同時段丟入垃圾統計圖錯誤：", e)
    
    # 2. 垃圾分類次數 (長條圖)
    try:
        df_log = pd.read_sql_query("SELECT category, times FROM trash_log", conn)
        plt.figure(figsize=(8, 6))
        plt.bar(df_log["category"], df_log["times"])
        plt.title("垃圾分類次數", fontproperties=font_prop)
        plt.xlabel("垃圾類型", fontproperties=font_prop)
        plt.ylabel("分類次數", fontproperties=font_prop)
        plt.xticks(fontproperties=font_prop)
        plt.yticks(fontproperties=font_prop)
        plt.tight_layout()
        chart2_path = os.path.join(output_folder, "垃圾分類次數.png")
        plt.savefig(chart2_path)
        plt.close()
        print(f"圖表已儲存：{chart2_path}")
    except Exception as e:
        print("產生垃圾分類次數圖錯誤：", e)
    
    # 3. 垃圾桶滿溢事件次數統計數據 (長條圖)
    try:
        df_bin = pd.read_sql_query("SELECT bin_type FROM bin_events WHERE event_type='full'", conn)
        df_bin_grouped = df_bin.groupby("bin_type").size().reset_index(name="count")
        plt.figure(figsize=(8, 6))
        plt.bar(df_bin_grouped["bin_type"], df_bin_grouped["count"], color="orange")
        plt.title("垃圾桶滿溢事件次數統計數據", fontproperties=font_prop)
        plt.xlabel("垃圾桶類型", fontproperties=font_prop)
        plt.ylabel("滿溢次數", fontproperties=font_prop)
        plt.xticks(fontproperties=font_prop)
        plt.yticks(fontproperties=font_prop)
        plt.tight_layout()
        chart3_path = os.path.join(output_folder, "垃圾桶滿溢事件次數統計數據.png")
        plt.savefig(chart3_path)
        plt.close()
        print(f"圖表已儲存：{chart3_path}")
    except Exception as e:
        print("產生垃圾桶滿溢事件次數統計數據圖錯誤：", e)
    
    # 4. 垃圾被丟次數 (長條圖)
    try:
        df_events_cat = pd.read_sql_query("SELECT category FROM trash_events", conn)
        df_events_cat_grouped = df_events_cat.groupby("category").size().reset_index(name="count")
        plt.figure(figsize=(8, 6))
        plt.bar(df_events_cat_grouped["category"], df_events_cat_grouped["count"], color="green")
        plt.title("垃圾被丟次數", fontproperties=font_prop)
        plt.xlabel("垃圾類型", fontproperties=font_prop)
        plt.ylabel("次數", fontproperties=font_prop)
        plt.xticks(fontproperties=font_prop)
        plt.yticks(fontproperties=font_prop)
        plt.tight_layout()
        chart4_path = os.path.join(output_folder, "垃圾被丟次數.png")
        plt.savefig(chart4_path)
        plt.close()
        print(f"圖表已儲存：{chart4_path}")
    except Exception as e:
        print("產生垃圾被丟次數圖錯誤：", e)
    
    # 5. 不同時段滿溢度 (折線圖)
    try:
        df_bin_time = pd.read_sql_query("SELECT timestamp FROM bin_events WHERE event_type='full'", conn)
        df_bin_time['timestamp'] = pd.to_datetime(df_bin_time['timestamp'])
        df_bin_time['hour'] = df_bin_time['timestamp'].dt.hour
        bin_overflow_by_hour = df_bin_time.groupby("hour").size().reset_index(name="count")
        bin_overflow_by_hour = bin_overflow_by_hour.sort_values("hour")
        plt.figure(figsize=(10, 6))
        plt.plot(bin_overflow_by_hour["hour"], bin_overflow_by_hour["count"], marker="o", color="red")
        plt.title("不同時段滿溢度", fontproperties=font_prop)
        plt.xlabel("時段（小時）", fontproperties=font_prop)
        plt.ylabel("滿溢次數", fontproperties=font_prop)
        plt.xticks(fontproperties=font_prop)
        plt.yticks(fontproperties=font_prop)
        plt.tight_layout()
        chart5_path = os.path.join(output_folder, "不同時段滿溢度.png")
        plt.savefig(chart5_path)
        plt.close()
        print(f"圖表已儲存：{chart5_path}")
    except Exception as e:
        print("產生不同時段滿溢度圖錯誤：", e)
    
    conn.close()
    return output_folder

# ------------------ 主程式運行 ------------------
try:
    print("\n系統啟動中...")
    text_display("系統啟動中...")
    while True:
        text_display("  系統正常\n  請投入垃圾...")
        dist = distance()
        print(dist)
        if dist < 20:
            detect_run()
            text_display("  系統正常\n  請投入垃圾...")
            upload_to_drive()
            garbage_levels()
        time.sleep(0.05)
except KeyboardInterrupt:
    print("🛑 程式已停止")
    text_display("\n程式已停止...")
    # 先產生圖表，並取得圖表資料夾路徑
    charts_folder = generate_charts()
    # 上傳圖表資料夾到 Google Drive
    upload_folder(charts_folder, GOOGLE_DRIVE_FOLDER_ID)
    send_line(generate_report())
    clear_old_data()  # 清除資料但保留表格結構
    upload_to_drive()
except Exception as e:
    print(f"發生例外：{e}")
    charts_folder = generate_charts()
    upload_folder(charts_folder, GOOGLE_DRIVE_FOLDER_ID)
    send_line(generate_report())
    clear_old_data()
    upload_to_drive()
