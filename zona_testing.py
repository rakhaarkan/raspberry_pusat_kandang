import adafruit_dht
import board
import time

# Jika DHT22 pada pin GPIO4
dht = adafruit_dht.DHT22(board.D4)

while True:
    try:
        suhu = dht.temperature
        lembab = dht.humidity
        print("Suhu:", suhu, "C")
        print("Lembab:", lembab, "%")
    except Exception as e:
        print("Gagal membaca:", e)
    time.sleep(2)
