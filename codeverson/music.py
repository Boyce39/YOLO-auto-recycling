from gpiozero import TonalBuzzer
from gpiozero.tones import Tone
from time import sleep

buzzer = TonalBuzzer(20)

songi = [
    ("E4", 0.6), ("G4", 0.6), ("E4", 0.6), ("C4", 0.6),  
    ("A3", 0.6), ("C4", 0.6), ("E4", 0.6), ("D4", 0.6),  
    ("B3", 0.6), ("D4", 0.6), ("F4", 0.6), ("E4", 0.8)   
]

song = [
    ("C4", 0.2), ("D4", 0.2), ("E4", 0.2), ("G4", 0.4),  
    ("E4", 0.2), ("D4", 0.2), ("C4", 0.4), 
    ("A3", 0.2), ("C4", 0.2), ("E4", 0.2), ("F4", 0.4),  
    ("E4", 0.2), ("C4", 0.2), ("A3", 0.4)   
]

for note, duration in song:
    buzzer.play(Tone(note))
    sleep(duration)
buzzer.close()
buzzer.stop()
buzzer.close()
