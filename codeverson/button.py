from gpiozero import Button
import time

buttons = {
    "塑膠": Button(17, pull_up=True),
    "紙類": Button(27, pull_up=True),
    "金屬": Button(22, pull_up=True),
    "一般": Button(5, pull_up=True)
}

def button_pressed(trash_type):
    print(f"✅ {trash_type} 按鈕被按下！")

for trash_type, button in buttons.items():
    button.when_pressed = lambda trash_type=trash_type: button_pressed(trash_type)

print("📢 按下按鈕來測試垃圾分類...")
while True:
    time.sleep(0.1)  # 避免 CPU 過載
