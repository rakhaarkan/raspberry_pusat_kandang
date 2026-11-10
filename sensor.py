from variabel_global import gl
import requests
import httpx

async def cuaca():
    url = "http://api.weatherapi.com/v1/current.json"
    params = {
        "key": "d471518f522047cdaca135243240705",
        "q": "godean",
        "aqi": "no"
    }

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=params)  # ✅ Non-blocking
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

def update_trend_dan_selisih():
    """
    Menghitung tren suhu dan kelembapan berdasarkan data historis.
    Jika data belum mencapai 10 menit, gunakan data paling awal yang tersedia.
    """

    # 1. Tambahkan data baru ke history
    gl.hist_suhu_dalam.append(gl.suhu_dalam)
    gl.hist_suhu_luar.append(gl.suhu_luar)
    gl.hist_kelembapan_dalam.append(gl.kelembapan_dalam)
    gl.hist_kelembapan_luar.append(gl.kelembapan_luar)

    # 2. Gunakan data paling pertama sebagai pembanding (meski kurang dari 10)
    idx_awal = 0  # index paling awal selalu 0

    # Jika history < 2 data, tidak bisa hitung tren
    if len(gl.hist_suhu_dalam) < 2:
        gl.trend_suhu_dalam_10m = 0.0
        gl.trend_suhu_luar_10m = 0.0
        gl.trend_kelembapan_dalam_10m = 0.0
        gl.trend_kelembapan_luar_10m = 0.0
    else:
        # Trend = data terbaru - data paling awal yang tersedia
        gl.trend_suhu_dalam_10m = gl.suhu_dalam - gl.hist_suhu_dalam[idx_awal]
        gl.trend_suhu_luar_10m = gl.suhu_luar - gl.hist_suhu_luar[idx_awal]
        gl.trend_kelembapan_dalam_10m = gl.kelembapan_dalam - gl.hist_kelembapan_dalam[idx_awal]
        gl.trend_kelembapan_luar_10m = gl.kelembapan_luar - gl.hist_kelembapan_luar[idx_awal]

    # 3. Hitung selisih suhu & kelembapan sekarang
    gl.selisih_suhu_luar_dalam = gl.suhu_luar - gl.suhu_dalam
    gl.selisih_kelembapan_luar_dalam = gl.kelembapan_luar - gl.kelembapan_dalam
    
    if(gl.trend_suhu_dalam_10m > 5 or gl.trend_suhu_dalam_10m < -5):
        gl.trend_suhu_dalam_10m = 0.0
    if(gl.trend_suhu_luar_10m > 5 or gl.trend_suhu_luar_10m < -5):
        gl.trend_suhu_luar_10m = 0.0
    if(gl.trend_kelembapan_dalam_10m > 40 or gl.trend_kelembapan_dalam_10m < -40):
        gl.trend_kelembapan_dalam_10m = 0.0
    if(gl.trend_kelembapan_luar_10m > 40 or gl.trend_kelembapan_luar_10m < -40):
        gl.trend_kelembapan_luar_10m = 0.0

def kelola_suhu_acuan():
    if gl.usia_ayam >= 10:
        # Prioritas suhu atas, fallback suhu luar, fallback default
        if gl.suhu_tengah_atas != 0:
            gl.suhu_acuan = gl.suhu_tengah_atas
        elif gl.suhu_atas != 0:
            gl.suhu_acuan = gl.suhu_atas
        elif gl.suhu_luar != 0:
            gl.suhu_acuan = gl.suhu_luar
        else:
            gl.suhu_acuan = 30.0
    else:
        # Rata-rata sensor aktif seperti sebelumnya
        values = []
        if gl.suhu_atas != 0:
            values.append(gl.suhu_atas)
        if gl.suhu_luar != 0:
            values.append(gl.suhu_luar)

        if values:
            gl.suhu_acuan = sum(values) / len(values)
        else:
            gl.suhu_acuan = 30.0

print("sensor.py dimuat.")