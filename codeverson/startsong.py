from gpiozero import TonalBuzzer
from gpiozero.tones import Tone
from time import sleep
buzzer = TonalBuzzer(20)
song = [
    ("C4", 0.2), ("D4", 0.2), ("E4", 0.2), ("G4", 0.4),  
    ("E4", 0.2), ("D4", 0.2), ("C4", 0.4), 
    ("A3", 0.2), ("C4", 0.2), ("E4", 0.2), ("F4", 0.4),  
    ("E4", 0.2), ("C4", 0.2), ("A3", 0.4)   
]
for note, duration in song:
    buzzer.play(Tone(note))
    sleep(duration)
buzzer.stop()
buzzer.close()
