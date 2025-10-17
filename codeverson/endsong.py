from gpiozero import TonalBuzzer
from gpiozero.tones import Tone
from time import sleep
buzzer = TonalBuzzer(20)
song= [
    ("E4", 0.6), ("G4", 0.6), ("E4", 0.6), ("C4", 0.6),  
    ("A3", 0.6), ("C4", 0.6), ("E4", 0.6), ("D4", 0.6),  
    ("B3", 0.6), ("D4", 0.6), ("F4", 0.6), ("E4", 0.6) ,  ("C4", 1)]
for note, duration in song:
    buzzer.play(Tone(note))
    sleep(duration)
buzzer.stop()
buzzer.close()
