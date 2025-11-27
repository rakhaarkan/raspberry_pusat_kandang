import requests
import json
import time
import datetime
import random
from variabel_global import gl
import penyimpanan_data as pd
import database_sqlite as db

# Konfigurasi Channel ThingSpeak
CHANNEL_ID = 2172969
WRITE_API_KEY = "BYKB03MQ0IA4X5YD"
THINGSPEAK_URL = "https://api.thingspeak.com/update"

def pengolah_json():
    db.baca_sql_sensor()
    """Konversi struktur pengolah_json Arduino ke Python + simpan 1 JSON besar."""

    # ----------- Bagian mirip Arduino: RPM, tanggal, mapping ------------
    gl.rpm_kipas = [0] * 11  # index 1..10 dipakai
    gl.grafik_waktu[1] = gl.jam

    tanggal_masuk_ayam = f"{gl.tanggal_masuk_ayam_tahun}-{gl.tanggal_masuk_ayam_bulan}-{gl.tanggal_masuk_ayam_hari}"

    # -------------------------------- json_sensor_1 -------------------------------
    json_besar = {
        "dat": [
            tanggal_masuk_ayam,
            gl.mode_kandang
        ],

        "shu": [
            pd._to_int_no_decimal(gl.suhu_atas),
            pd._to_int_no_decimal(gl.suhu_bawah),
            pd._to_int_no_decimal(gl.suhu_luar),
            pd._to_int_no_decimal(gl.suhu_acuan),
        ],

        "klb": [
            pd._to_int_no_decimal(gl.kelembapan_atas + random.randint(-10, 10)),
            pd._to_int_no_decimal(gl.kelembapan_bawah),
            pd._to_int_no_decimal(gl.kelembapan_luar + random.randint(-5, 5)),
            pd._to_int_no_decimal(gl.kelembapan_greenhouse),
        ],

        "dhi": [
            gl.data_HI_atas,
            gl.data_HI_bawah,
            gl.data_HI_luar + random.randint(-5, 5),
            gl.data_HI_greenhouse,
        ],

        "air": [
            gl.liter_tong_atas,
            gl.liter_tong_bawah,
            gl.persen_air_atas,
            gl.persen_air_bawah,
            gl.kecepatan_minum_atas,
            gl.kecepatan_minum_bawah,
        ],

        "kps": [0, 0, 0, 0, 0],

        "lst": [
            gl.voltage,
            gl.current,
            gl.power,
            gl.energy,
            gl.frequency,
            gl.pf,
            gl.kecepatan_listrik_atas,
            gl.kwh_jam,
            gl.kwh_harian,
            "pln"
        ],

        "agn": [
            gl.kecepatan_angin_atas,
            100,
            100
        ],
    
        "gwk": [gl.grafik_waktu[1]],

        "gsa": [gl.grafik_suhu_atas[i] for i in range(1, 24)],

        "gka": [gl.grafik_kelembapan_luar[i] for i in range(1, 24)],
    
        "gsb": [gl.grafik_suhu_luar[i] for i in range(1, 24)],

        "cry": [
            gl.lampu_luar,
            gl.indikator_cuaca,
            gl.kode_cuaca,
            gl.teks_cuaca
        ],
   
        "kpa": [
            gl.mode_kandang,
            gl.usia_ayam,
            gl.target_suhu,
            gl.suhu_minimal,
            gl.suhu_maksimal,
            gl.kipas[0],
            gl.kipas[1],
            gl.kipas[2],
            gl.kipas[3],
            gl.kipas[4],
            gl.status_timer,
            gl.waktu_hidup,
            gl.waktu_mati,
            gl.detail_kipas,
            gl.debug_155,
        ],

        "mtd": [
            gl.harga_pakan_kg,
            gl.jumlah_ayam_awal,
            gl.harga_obat_ayam,
            gl.jumlah_ayam_mati,
            gl.harga_bibit_ayam,
            gl.jumlah_pakan_sak,
            gl.harga_kontrak_ayam,
            gl.bobot_rata_rata,
            gl.blok_kandang,
            gl.jumlah_ayam_dipanen
        ],

        "bbt": [
            gl.bobot_timbang,
            gl.bobot_rata_rata_timbang,
            gl.jumlah_sample_timbang,
            *gl.sebaran_bobot,
            0
        ]
        #"timestamp": datetime.now().isoformat()
    }
    
    gl.json_thingspeak = json_besar
    
    # ----------------------- Simpan ke file -----------------------------
    with open("sample_json_thg.json", "w") as f:
        json.dump(json_besar, f, separators=(",", ":"), ensure_ascii=False)

    print("[pengolah_json] JSON besar berhasil disimpan ? sample_json_thg.json")
    


def split_json_to_fields(json_string, parts=8, size=240):
    """Potong JSON panjang menjadi maksimal 8 bagian, masing <= size chars."""

    # Jika input adalah dict, convert ke string JSON
    if isinstance(json_string, dict):
        json_string = json.dumps(json_string, separators=(",", ":"))

    chunks = []
    for i in range(0, len(json_string), size):
        chunks.append(json_string[i:i+size])

    # Pastikan jumlah chunk sesuai parts
    while len(chunks) < parts:
        chunks.append("")

    return chunks[:parts]



def kirim_thingspeak():
    pengolah_json()

    json_big = gl.json_thingspeak
    fields = split_json_to_fields(json_big)

    payload = {
        "api_key": WRITE_API_KEY,
        "field1": fields[0],
        "field2": fields[1],
        "field3": fields[2],
        "field4": fields[3],
        "field5": fields[4],
        "field6": fields[5],
        "field7": fields[6],
        "field8": fields[7],
        "status": "okay"
    }

    try:
        response = requests.post(THINGSPEAK_URL, data=payload)
        print("[ThingSpeak] Status:", response.text)
        response.close()
    except Exception as e:
        print("[ThingSpeak] ERROR:", e)

kirim_thingspeak()
