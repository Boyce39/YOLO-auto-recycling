import gpiod
import time
import os

# 定義 GPIO 腳位（使用 BCM 編號）
TRIG_PIN = 16  # 超音波發送腳位
ECHO_PIN = 18  # 超音波接收腳位

# 開啟 GPIO 晶片
chip = gpiod.Chip("gpiochip0")

# 設定 GPIO 腳位模式
trig_line = chip.get_line(TRIG_PIN)
echo_line = chip.get_line(ECHO_PIN)

trig_line.request(consumer="trig", type=gpiod.LINE_REQ_DIR_OUT)  # 設定 TRIG 為輸出
echo_line.request(consumer="echo", type=gpiod.LINE_REQ_DIR_IN)   # 設定 ECHO 為輸入

def get_distance():
    """測量距離"""
    # 發送超音波信號（觸發 10 微秒的高電位）
    trig_line.set_value(1)
    time.sleep(0.00001)
    trig_line.set_value(0)

    # 等待 Echo 變高，記錄開始時間
    start_time = time.time()
    while echo_line.get_value() == 0:
        start_time = time.time()

    # 等待 Echo 變低，記錄結束時間
    end_time = time.time()
    while echo_line.get_value() == 1:
        end_time = time.time()

    # 計算距離（時間 * 聲速 / 2）
    duration = end_time - start_time
    distance = (duration * 34300) / 2  # 單位: 公分
    return distance

try:
    while True:
        dist = get_distance()  # 取得距離
        print(f"Distance: {dist:.2f} cm")  # 顯示測量結果
        
        if dist < 10:  # 如果距離小於 10 公分，執行 main.py
            print("物體偵測到！執行 main.py")
            os.system("python3 main.py")  
            time.sleep(5)  # 避免連續觸發，等待 5 秒
        
        time.sleep(0.1)  # 每 0.1 秒測量一次

except KeyboardInterrupt:
    print("程式已停止")
    trig_line.release()
    echo_line.release()