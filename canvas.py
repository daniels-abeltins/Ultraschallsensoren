import sqlite3
import time
import math
import tkinter as tk
import RPi.GPIO as GPIO


# Setup pins
LED = 21
SENSORS = {
    'sensor1': {'trigger': 23, 'echo': 24, 'pos_x': 20, 'pos_y': 0},
    'sensor2': {'trigger': 26, 'echo': 22, 'pos_x':  0, 'pos_y': 20}
}
# Connect to database
conn = sqlite3.connect('entfernungen.db')
cursor = conn.cursor()


def setup(ssh=False):
    # GPIO
    GPIO.setmode(GPIO.BCM)
    for sensor in SENSORS.values():
        GPIO.setup(sensor['trigger'], GPIO.OUT)
        GPIO.setup(sensor['echo'], GPIO.IN)
    GPIO.setup(LED, GPIO.OUT)

    # Datenbank
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messwerte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distance_sensor_one REAL,
            distance_sensor_two REAL,
            batch_number INTEGER
        )
    ''')
    conn.commit()
    
    # Visualisierung
    if not ssh:
        root = tk.Tk()
        root.title("Canvas")
        canvas = tk.Canvas(root, width=400, height=400, bg="white")
        canvas.pack()
    return canvas if not ssh else None


def schnittpunkt(dist1, dist2):
    # Abstand der Mittelpunkte
    dx = SENSORS['sensor2']['pos_x'] - SENSORS['sensor1']['pos_x']
    dy = SENSORS['sensor2']['pos_y'] - SENSORS['sensor1']['pos_y']
    d = math.hypot(dx, dy)
    
    # Abstand von (x0, y0) zur Linie der Schnittpunkte
    a = (dist1**2 - dist2**2 + d**2) / (2*d)
    # Höhe des Schnittpunkt-Dreiecks
    h = math.sqrt(max(0.0, dist1**2 - a**2))
    
    # Basis-Punkt auf vder Verbindungslinie
    xm = SENSORS['sensor1']['pos_x'] + a * dx / d
    ym = SENSORS['sensor1']['pos_y'] + a * dy / d
    
    #Versatzvektoren für die beiden Schnittpunkte
    rx = -dy * (h / d)
    ry = dx * (h / d)
    
    # 2 Endpositionen, da immer 2 Schnittpunkte vorhanden sind
    p1 = (xm + rx + 100, ym + ry + 100)
    p2 = (xm - rx + 100, ym - ry + 100)
    
    # Der höchste Wert wird immer der Richtige sein
    return max(p1, p2)


def messen(trigger_pin, echo_pin):
    GPIO.output(trigger_pin, False)
    time.sleep(0.05)
    # Trigger senden
    GPIO.output(trigger_pin, True)
    time.sleep(0.00001)
    GPIO.output(trigger_pin, False)

    # Starte Echo
    timeout = time.time() + 1
    while GPIO.input(echo_pin) == 0:
        if time.time() > timeout:
            print("timeout while 1")
            print(GPIO.input(echo_pin))
            raise TimeoutError("timeout while 2")
        pass
    start_time = time.time()

    # Warte auf Echo Ende
    timeout = time.time() + 1
    while GPIO.input(echo_pin) == 1:
        if time.time() > timeout:
            print("timeout while 2")
            raise TimeoutError("timeout while 2")
        pass
    stop_time = time.time()

    # Zeitunterschied
    elapsed = stop_time - start_time
    print(stop_time, start_time, elapsed)
    entfernung = (elapsed * 34300) / 2  # Schallgeschwindigkeit 34300 cm/s

    return round(entfernung, 2)
    

def draw(canvas, x, y, size=1, color="black"):
    canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)


def loop(canvas):
    try:
        while True:
            sensor_data = {}
            
            # Messen
            for name, pins in SENSORS.items():
                entfernung = messen(pins['trigger'], pins['echo'])
                print(f"{name}: {entfernung} cm")
                
                # Über- bzw. Unterschreitung der Grenzwerte
                if not entfernung or entfernung > 100 or entfernung < 4:
                    GPIO.output(LED, True)
                    sensor_data[name] = 0
                else:
                    sensor_data[name] = entfernung

            # In Datenbank speichern
            cursor.execute('''
                INSERT INTO messwerte (distance_sensor_one, distance_sensor_two, batch_number)
                VALUES (?, ?, ?)
            ''', (sensor_data['sensor1'], sensor_data['sensor2'], 1))
            conn.commit()

            # Visualisieren
            position = schnittpunkt(sensor_data['sensor1'], sensor_data['sensor2'])
            draw(canvas, position[0], position[1]) if canvas else print(position)
            canvas.update()

            time.sleep(0.3) 
            GPIO.output(LED, False)

    except KeyboardInterrupt:
        print("Messung beendet.")


def main():
    canvas = setup(False)
    loop(canvas)
    GPIO.cleanup()
    conn.close()
   

if __name__ == "__main__":
    main()
