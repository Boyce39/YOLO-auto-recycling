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
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from playsound import playsound

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
font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
font = ImageFont.truetype(font_path, 15)
LINETOKEN = "naobDbheaBWNXenoF04pMkG7iwyBqQXhRc1SdDalm89"

trash_types = {
    "1": "紙容器回收桶", 
    "2": "塑膠回收桶", 
    "3": "金屬回收桶", 
    "4": "一般垃圾桶"
}

buttons = {
    "塑膠類": Button(17, pull_up=True),
    "紙容器": Button(27, pull_up=True),
    "金屬類": Button(22, pull_up=True),
}

# ------------------ 事件記錄函式 ------------------
def log_trash_event(category):
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
        "紙容器": 6800,
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
    default_trash_types = ["紙容器", "塑膠類", "金屬類", "一般垃圾"]
    for category in default_trash_types:
        cursor.execute("INSERT OR IGNORE INTO trash_log (category, times) VALUES (?, 0)", (category,))
    default_bins = ["紙容器回收桶", "塑膠回收桶", "金屬回收桶", "一般垃圾桶"]
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
    playsound('/home/pi/Desktop/yolo_project/soung/10s.mp3')
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
    class_mapping = {0: '金屬類', 1: '紙容器', 2: '塑膠類'}
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
    if final=='一般垃圾':
        playsound('/home/pi/Desktop/yolo_project/soung/garbage.mp3')
    elif final=='金屬類':
        playsound('/home/pi/Desktop/yolo_project/soung/metal.mp3')
    elif final=='紙容器':
        playsound('/home/pi/Desktop/yolo_project/soung/paper.mp3')
    else:
        playsound('/home/pi/Desktop/yolo_project/soung/plastic.mp3')
    print(f"📦 最終分類結果：{final}")
    log_trash_event(final)
    save_training_data(frame, det_info, final)
    save_data(final)
    os.system("python3 endsong.py &")
    text_display(f"分類結果：\n       {final}")
    move(final)

def save_training_data(image, detection, final_class, manual_classification=False):
    if isinstance(final_class, list):
        final_class = final_class[0]
    if not detection:
        print("無偵測到任何座標，故不儲存訓練資料")
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
        print(f"無符合 {final_class} 的 bbox（未達置信度門檻 0.6），圖片已存，但不寫入標註。")
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
            class_mapping = {'金屬類': 0, '紙容器': 1, '塑膠類': 2}
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
            if trash_type=='一般垃圾桶':
                playsound('/home/pi/Desktop/yolo_project/soung/garbagefull.mp3')
            elif trash_type=='金屬回收桶':
                playsound('/home/pi/Desktop/yolo_project/soung/metalfull.mp3')
            elif trash_type=='紙容器回收桶':
                playsound('/home/pi/Desktop/yolo_project/soung/paperfull.mp3')
            else:
                playsound('/home/pi/Desktop/yolo_project/soung/plasticfull.mp3')
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
            playsound('/home/pi/Desktop/yolo_project/soung/clean.mp3')
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
            playsound('/home/pi/Desktop/yolo_project/soung/update.mp3')
            print(f" 偵測到 {len(label_files)} 個標註檔案，開始上傳")
            text_display("資料自動上傳中")
            upload_folder(IMAGES_FOLDER, GOOGLE_DRIVE_FOLDER_ID)
            upload_folder(LABELS_FOLDER, GOOGLE_DRIVE_FOLDER_ID)
            shutil.rmtree(IMAGES_FOLDER)
            shutil.rmtree(LABELS_FOLDER)
            os.makedirs(IMAGES_FOLDER)
            os.makedirs(LABELS_FOLDER)
            print("料夾已清空，等待新的訓練數據。")
            playsound('/home/pi/Desktop/yolo_project/soung/finish.mp3')
        else:
            print(f"數據僅有 {len(label_files)} 個檔案，未達上傳條件，跳過")
    except KeyboardInterrupt:
        print(" 手動中斷，停止上傳...")

# ------------------ 圖表產生（整合散點圖與長條圖） ------------------
def generate_charts():
    # 設定中文字型
    font_path = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
    font_prop = fm.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = font_prop.get_name()
    plt.rcParams['axes.unicode_minus'] = False

    # 建立圖表輸出資料夾（以時間戳命名）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_folder = f"/home/pi/Desktop/yolo_project/data/{timestamp}"
    os.makedirs(output_folder, exist_ok=True)
    print(f"建立圖表資料夾: {output_folder}")

    # 連接資料庫並讀取事件資料與統計數據
    conn = sqlite3.connect("garbage_data.db")
    try:
        df_trash = pd.read_sql_query("SELECT timestamp, category FROM trash_events", conn)
        df_trash['timestamp'] = pd.to_datetime(df_trash['timestamp'])
    except Exception as e:
        print("讀取垃圾分類事件資料錯誤：", e)
        df_trash = pd.DataFrame(columns=['timestamp', 'category'])
    try:
        df_bin = pd.read_sql_query("SELECT timestamp, bin_type FROM bin_events WHERE event_type='full'", conn)
        df_bin['timestamp'] = pd.to_datetime(df_bin['timestamp'])
    except Exception as e:
        print("讀取垃圾桶滿溢事件資料錯誤：", e)
        df_bin = pd.DataFrame(columns=['timestamp', 'bin_type'])
    try:
        df_trash_overall = pd.read_sql_query("SELECT category, times FROM trash_log", conn)
    except Exception as e:
        print("讀取垃圾分類統計資料錯誤：", e)
        df_trash_overall = pd.DataFrame(columns=['category', 'times'])
    try:
        df_bin_overall = pd.read_sql_query("SELECT bin_type, times FROM trash_full", conn)
    except Exception as e:
        print("讀取垃圾桶滿溢統計資料錯誤：", e)
        df_bin_overall = pd.DataFrame(columns=['bin_type', 'times'])
    conn.close()

    # 建立 2×2 子圖整合圖表
    fig, axs = plt.subplots(2, 2, figsize=(18, 12))
    
    # ---------- (1) 垃圾分類事件散點圖 ----------
    if not df_trash.empty:
        unique_trash = sorted(df_trash["category"].unique())
        mapping_trash = {cat: i for i, cat in enumerate(unique_trash)}
        df_trash["category_val"] = df_trash["category"].map(mapping_trash)
        axs[0, 0].scatter(df_trash["timestamp"], df_trash["category_val"], color='blue', s=80)
        axs[0, 0].set_xlabel("時間", fontproperties=font_prop)
        axs[0, 0].set_ylabel("回收物種類", fontproperties=font_prop)
        axs[0, 0].set_title("垃圾分類事件散點圖", fontproperties=font_prop)
        axs[0, 0].xaxis_date()
        axs[0, 0].tick_params(axis='x', rotation=45)
        axs[0, 0].set_yticks(list(mapping_trash.values()))
        axs[0, 0].set_yticklabels(list(mapping_trash.keys()), fontproperties=font_prop)
        for idx, row in df_trash.iterrows():
            axs[0, 0].annotate(row["timestamp"].strftime("%H:%M"),
                               (row["timestamp"], row["category_val"]),
                               textcoords="offset points", xytext=(5, 5),
                               ha='left', fontsize=9, fontproperties=font_prop)
    else:
        axs[0, 0].text(0.5, 0.5, "無垃圾分類事件資料", transform=axs[0, 0].transAxes, ha="center", va="center")
    
    # ---------- (2) 垃圾桶滿溢事件散點圖 ----------
    if not df_bin.empty:
        unique_bin = sorted(df_bin["bin_type"].unique())
        mapping_bin = {b: i for i, b in enumerate(unique_bin)}
        df_bin["bin_val"] = df_bin["bin_type"].map(mapping_bin)
        axs[0, 1].scatter(df_bin["timestamp"], df_bin["bin_val"], color='red', s=80)
        axs[0, 1].set_xlabel("時間", fontproperties=font_prop)
        axs[0, 1].set_ylabel("垃圾桶種類", fontproperties=font_prop)
        axs[0, 1].set_title("垃圾桶滿溢事件散點圖", fontproperties=font_prop)
        axs[0, 1].xaxis_date()
        axs[0, 1].tick_params(axis='x', rotation=45)
        axs[0, 1].set_yticks(list(mapping_bin.values()))
        axs[0, 1].set_yticklabels(list(mapping_bin.keys()), fontproperties=font_prop)
        for idx, row in df_bin.iterrows():
            axs[0, 1].annotate(row["timestamp"].strftime("%H:%M"),
                               (row["timestamp"], row["bin_val"]),
                               textcoords="offset points", xytext=(5, 5),
                               ha='left', fontsize=9, fontproperties=font_prop)
    else:
        axs[0, 1].text(0.5, 0.5, "無垃圾桶滿溢事件資料", transform=axs[0, 1].transAxes, ha="center", va="center")
    
# ---------- (3) 垃圾分類整體統計長條圖 ----------
    if not df_trash_overall.empty:
        axs[1, 0].bar(df_trash_overall["category"], df_trash_overall["times"], color='skyblue')
        axs[1, 0].set_xlabel("垃圾分類", fontproperties=font_prop)
        axs[1, 0].set_ylabel("次數", fontproperties=font_prop)
        axs[1, 0].set_title("垃圾分類整體統計長條圖", fontproperties=font_prop)
        axs[1, 0].yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        axs[1, 0].tick_params(axis='x', rotation=45)

    # ✅ 加上這行來指定 X 軸標籤字型
        axs[1, 0].set_xticklabels(df_trash_overall["category"], fontproperties=font_prop)
    else:
        axs[1, 0].text(0.5, 0.5, "無垃圾分類統計資料", transform=axs[1, 0].transAxes, ha="center", va="center")

    # ---------- (4) 垃圾桶滿溢整體統計長條圖 ----------
    if not df_bin_overall.empty:
        axs[1, 1].bar(df_bin_overall["bin_type"], df_bin_overall["times"], color='salmon')
        axs[1, 1].set_xlabel("垃圾桶類型", fontproperties=font_prop)
        axs[1, 1].set_ylabel("次數", fontproperties=font_prop)
        axs[1, 1].set_title("垃圾桶滿溢整體統計長條圖", fontproperties=font_prop)
        axs[1, 1].yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        axs[1, 1].tick_params(axis='x', rotation=45)

        # ✅ 加上這行來指定 X 軸標籤字型
        axs[1, 1].set_xticklabels(df_bin_overall["bin_type"], fontproperties=font_prop)
    else:
        axs[1, 1].text(0.5, 0.5, "無垃圾桶滿溢統計資料", transform=axs[1, 1].transAxes, ha="center", va="center")

    
    plt.tight_layout()
    # 若底部標籤仍被截斷，可調整底部邊距
    plt.subplots_adjust(bottom=0.15)
    integrated_chart_path = os.path.join(output_folder, "integrated_charts.png")
    plt.savefig(integrated_chart_path)
    plt.close()
    print(f"整合圖表已儲存：{integrated_chart_path}")
    return output_folder

# ------------------ 主程式運行 ------------------
try:
    print("\n系統啟動中...")
    playsound('/home/pi/Desktop/yolo_project/soung/open-1.mp3')
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
    charts_folder = generate_charts()
    upload_folder(charts_folder, GOOGLE_DRIVE_FOLDER_ID)
    send_line(generate_report())
    clear_old_data()
    upload_to_drive()
except Exception as e:
    print(f"發生例外：{e}")
    charts_folder = generate_charts()
    upload_folder(charts_folder, GOOGLE_DRIVE_FOLDER_ID)
    send_line(generate_report())
    clear_old_data()
    upload_to_drive()
