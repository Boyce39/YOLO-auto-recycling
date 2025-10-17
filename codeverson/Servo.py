from gpiozero import Servo
from time import sleep

servo = Servo(18)

while True:
    print("伺服馬達轉至最左邊")
    servo.min()
    sleep(1)
    
    print("伺服馬達轉至中央")
    servo.mid()
    sleep(1)
    
    print("伺服馬達轉至最右邊")
    servo.max()
    sleep(1)
