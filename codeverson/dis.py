from gpiozero import DistanceSensor
import time
import os

# 設定超音波感測器的 GPIO 腳位
TRIG_PIN = 23  # 觸發腳位（發送超音波）
ECHO_PIN = 24  # 回應腳位（接收回音）

# 初始化超音波感測器
sensor = DistanceSensor(echo=ECHO_PIN, trigger=TRIG_PIN)

def get_distance():
    """測量距離"""
    return sensor.distance * 100  # 轉換為公分

try:
    while True:
        dist = get_distance()  # 取得距離
        print(f"Distance: {dist:.2f} cm")  # 顯示測量結果
        
        if dist < 10:  # 如果距離小於 10 公分，執行 main.py
            print("執行 main.py")
            #os.system("python3 main.py")  
            time.sleep(5)  # 避免連續觸發，等待 5 秒
        
        time.sleep(0.1)  # 每 0.1 秒測量一次

except KeyboardInterrupt:
    print("程式已停止")