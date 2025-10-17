import time
from gpiozero import DistanceSensor

# ? 設定 GPIO 腳位
TRIG = 23  # 單一 TRIG 觸發
ECHO_PINS = [24, 25]  # 多個 ECHO 腳位

# ? 滿溢判斷參數
HEIGHT = 50  # 垃圾桶總高度 (cm)
FULL = 10  # 滿溢臨界值 (當測量距離 ? 10cm 時，表示垃圾桶滿了)

# ? 取得距離並判斷垃圾桶狀態
def garbage_levels():
    status = []
    
    for i, echo_pin in enumerate(ECHO_PINS):
        # **使用 `TRIG=23` 分別觸發不同的 `ECHO`**
        sensor = DistanceSensor(echo=echo_pin, trigger=TRIG)
        time.sleep(0.1)  # 讓感測器有時間穩定

        distance = sensor.distance * 100  # 轉換為 cm
        sensor.close()  # 釋放感測器資源，避免 GPIO 被佔用

        # **判斷垃圾桶狀態**
        if distance <= FULL:
            status.append(f"垃圾桶 {i+1}: ?? 已滿！請清理！")
        else:
            status.append(f"垃圾桶 {i+1}: ? 正常，距離: {distance:.1f} cm")

    return status

# ? 主要執行迴圈
try:
    while True:
        levels = garbage_levels()
        for level in levels:
            print(level)
        print("="*40)
        time.sleep(60)  # 每 60 秒檢查一次垃圾桶狀態

except KeyboardInterrupt:
    print("程式已停止")
