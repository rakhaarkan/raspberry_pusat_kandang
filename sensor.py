#import adafruit_dht
#import board
from variabel_global import gl
import requests

#dht = adafruit_dht.DHT22(board.D4)  # GPIO4

#while True:
 #   try:
  #      temp = dht.temperature
   #     hum  = dht.humidity
    #    print("Temp:", temp, "Humidity:", hum)
    #except Exception as e:
     #   print("Error:", e)

async def cuaca():
    print("mulai cuaca")
    url = "http://api.weatherapi.com/v1/current.json"
    params = {
        "key": "d471518f522047cdaca135243240705",
        "q": "godean",
        "aqi": "no"
    }

    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()

        # Ambil data cuaca
        gl.kode_cuaca = data["current"]["condition"]["code"]
        gl.teks_cuaca = data["current"]["condition"]["text"]
        suhu_luar_a = data["current"]["temp_c"]
        suhu_luar_b = data["current"]["feelslike_c"]
        gl.suhu_luar_cuaca = (suhu_luar_a + suhu_luar_b) / 2
        gl.suhu_luar = gl.suhu_luar_cuaca
        gl.kelembapan_luar = data["current"]["humidity"]

        print("Response:", data)
        print("Weather condition code:", gl.kode_cuaca)

    except Exception as e:
        print("Error:", e)
        return

    # daftar kode rawan
    weather_codes = [
        1066, 1069, 1072, 1087, 1114, 1117, 1153, 1168, 1171, 1183,
        1186, 1189, 1192, 1195, 1198, 1201, 1204, 1207, 1210, 1213,
        1216, 1219, 1222, 1225, 1237, 1243, 1246, 1249, 1252, 1255,
        1258, 1261, 1264, 1273, 1276, 1279, 1282
    ]

    # cek apakah cuaca rawan
    if gl.kode_cuaca in weather_codes:
        print("cuaca rawan petir, gunakan baterai")
        gl.indikator_cuaca = 1
    else:
        print("cuaca aman, gunakan listrik PLN")
        gl.indikator_cuaca = 0

    