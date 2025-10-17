import RPi.GPIO as GPIO
import time
import os  # 用於執行外部程式

# 定義 GPIO pin
TRIG_PIN = 18
ECHO_PIN = 24


GPIO.setmode(GPIO.BCM # 設定 GPIO 模式
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

def get_distance():
    # 發送超音波
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)
    
    # 等待 Echo 開始
    while GPIO.input(ECHO_PIN) == 0:
        start_time = time.time()
    
    # 等待 Echo 結束
    while GPIO.input(ECHO_PIN) == 1:
        end_time = time.time()
    
    # 計算距離
    duration = end_time - start_time
    distance = (duration * 34300) / 2  # 速度 * 時間 / 2 (單位: 公分)
    return distance

try:
    while True:
        dist = get_distance()
        print(f"Distance: {dist:.2f} cm")
        
        if dist < 10:  # 設定 10 公分為閾值
            print("Object detected! Running main.py...")
            os.system("python3 main.py")  # 執行 main.py
            time.sleep(5)  # 避免連續觸發，等待 5 秒
        
        time.sleep(0.1)  # 每 0.1 秒檢測一次

except KeyboardInterrupt:
    print("Program stopped by user")
    GPIO.cleanup()
