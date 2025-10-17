import gpiod
import time

# 設定 GPIO 編號（BCM 模式）
TRIG_PIN = 23  # GPIO23（對應 Pin 16）
ECHO_PIN = 12  # GPIO12（對應 Pin 32）

# 初始化 gpiod
chip = gpiod.Chip("gpiochip0")
trig = chip.get_line(TRIG_PIN)
echo = chip.get_line(ECHO_PIN)

trig.request(consumer="ultrasonic", type=gpiod.LINE_REQ_DIR_OUT)
echo.request(consumer="ultrasonic", type=gpiod.LINE_REQ_DIR_IN)

def measure_distance():
    """測量距離"""
    trig.set_value(1)
    time.sleep(0.00001)
    trig.set_value(0)

    start_time = time.time()
    timeout = start_time + 1  # 設定 1 秒超時

    while echo.get_value() == 0:
        if time.time() > timeout:
            print("⚠️ ECHO (GPIO12) 無法變為高電位，請檢查 TRIG 是否正常觸發")
            return None
        start_time = time.time()

    end_time = time.time()
    timeout = end_time + 1  # 設定 1 秒超時

    while echo.get_value() == 1:
        if time.time() > timeout:
            print("⚠️ ECHO (GPIO12) 無法變為低電位，請檢查 ECHO 接線")
            return None
        end_time = time.time()

    duration = end_time - start_time
    distance = (duration * 34300) / 2  # 34300 cm/s 為聲音速度
    return distance

try:
    while True:
        dist = measure_distance()
        if dist is not None:
            print(f"🏷️ 測量距離: {dist:.2f} cm")
        time.sleep(1)

except KeyboardInterrupt:
    print("🛑 程式已停止")
    trig.release()
    echo.release()
