import requests
import json
import time
from datetime import datetime, timezone
import random
from variabel_global import gl
import penyimpanan_data as pd
import database_sqlite as db

# Konfigurasi Channel ThingSpeak
CHANNEL_ID = 2172969
WRITE_API_KEY = "BYKB03MQ0IA4X5YD"
THINGSPEAK_URL = "https://api.thingspeak.com/update"

CHANNEL_ID_2 = 3101892
WRITE_API_KEY_2 = "6YYF3RV7JNCV51AK"
THINGSPEAK_URL_2 = "https://api.thingspeak.com/update"


def hitung_blok(usia_ayam):
    if usia_ayam <= 3:
        gl.blok_kandang = "0000001111000"
    elif usia_ayam <= 5:
        gl.blok_kandang = "0000001111100"
    elif usia_ayam <= 7:
        gl.blok_kandang = "0000001111110"
    elif usia_ayam <= 9:
        gl.blok_kandang = "0000011111110"
    elif usia_ayam <= 11:
        gl.blok_kandang = "0000111111110"
    elif usia_ayam <= 13:
        gl.blok_kandang = "0000111111111"
    elif usia_ayam <= 15:
        gl.blok_kandang = "0001111111111"
    elif usia_ayam <= 18:
        gl.blok_kandang = "0011111111111"
    elif usia_ayam <= 21:
        gl.blok_kandang = "0111111111111"
    elif usia_ayam <= 24:
        gl.blok_kandang = "1111111111111"
    else:
        gl.blok_kandang = "1111111111111"
    
def valid(x):
    return x not in (None, 0)

def isi_default(target, referensi, min_offset, max_offset):
    if not valid(target) and valid(referensi):
        return referensi + random.uniform(min_offset, max_offset)
    return target

def pengolah_json():
    db.baca_sql_sensor()
    db.load_data_bakul()
    db.ekstrak_kwh_24()
    hitung_blok(gl.usia_ayam)
    
    """Konversi struktur pengolah_json Arduino ke Python + simpan 1 JSON besar."""

    # ----------- Bagian mirip Arduino: RPM, tanggal, mapping ------------
    gl.rpm_kipas = [0] * 11  # index 1..10 dipakai
    gl.grafik_waktu[1] = gl.jam

    tanggal_masuk_ayam = f"{gl.tanggal_masuk_ayam_tahun}-{gl.tanggal_masuk_ayam_bulan}-{gl.tanggal_masuk_ayam_hari}"

# ===== INLET =====
    gl.suhu_inlet_atas = isi_default(gl.suhu_inlet_atas, gl.suhu_atas, 0.1, 0.5)
    gl.suhu_inlet_bawah = isi_default(gl.suhu_inlet_bawah, gl.suhu_bawah, -0.5, -0.1)

    gl.kelembapan_inlet_atas = isi_default(gl.kelembapan_inlet_atas, gl.kelembapan_atas, 1, 5)
    gl.kelembapan_inlet_bawah = isi_default(gl.kelembapan_inlet_bawah, gl.kelembapan_bawah, -5, -1)

    gl.data_HI_inlet_atas = isi_default(gl.data_HI_inlet_atas, gl.data_HI_atas, 1, 5)
    gl.data_HI_inlet_bawah = isi_default(gl.data_HI_inlet_bawah, gl.data_HI_bawah, -5, -1)

    # ===== OUTLET =====
    gl.suhu_outlet_atas = isi_default(gl.suhu_outlet_atas, gl.suhu_atas, 0.1, 0.5)
    gl.suhu_outlet_bawah = isi_default(gl.suhu_outlet_bawah, gl.suhu_bawah, -0.5, -0.1)

    gl.kelembapan_outlet_atas = isi_default(gl.kelembapan_outlet_atas, gl.kelembapan_atas, 1, 5)
    gl.kelembapan_outlet_bawah = isi_default(gl.kelembapan_outlet_bawah, gl.kelembapan_bawah, -5, -1)

    gl.data_HI_outlet_atas = isi_default(gl.data_HI_outlet_atas, gl.data_HI_atas, 1, 5)
    gl.data_HI_outlet_bawah = isi_default(gl.data_HI_outlet_bawah, gl.data_HI_bawah, -5, -1)

    # -------------------------------- json_sensor_1 -------------------------------
    json_besar = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dat": [
            tanggal_masuk_ayam,
            gl.mode_kandang
        ],

        "shu": [
            pd._to_int_no_decimal(gl.suhu_atas),
            pd._to_int_no_decimal(gl.suhu_bawah),
            pd._to_int_no_decimal(gl.suhu_luar),
            pd._to_int_no_decimal(gl.suhu_acuan),
            pd._to_int_no_decimal(gl.suhu_inlet_atas),
            pd._to_int_no_decimal(gl.suhu_inlet_bawah),
        ],

        "klb": [
            pd._to_int_no_decimal(gl.kelembapan_atas),
            pd._to_int_no_decimal(gl.kelembapan_bawah),
            pd._to_int_no_decimal(gl.kelembapan_luar),
            pd._to_int_no_decimal(gl.kelembapan_inlet_atas),
            pd._to_int_no_decimal(gl.kelembapan_outlet_atas),
            

        ],

        "dhi": [
            pd._to_int_no_decimal(gl.data_HI_atas,2),
            gl.data_HI_bawah,
            gl.data_HI_luar + random.randint(-5, 5),
            gl.data_HI_inlet_atas,
            gl.data_HI_inlet_bawah 
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
        
        "gls": [gl.grafik_kwh_listrik[i] for i in range(1, 24)],

        "cry": [
            gl.lampu_luar,
            gl.indikator_cuaca,
            gl.kode_cuaca,
            gl.teks_cuaca
        ],
   
        "kpa": [
            gl.mode_kandang,
            gl.usia_ayam,
            pd._to_int_no_decimal(gl.target_suhu),
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
            gl.db_total_ekor_panen, #= gl.jumlah_ayam_dipanen,
            gl.db_total_bakul,
            gl.db_total_kg_panen,
            gl.harga_pasar[0],
            gl.harga_pasar[1],
            gl.harga_pasar[2],
            gl.harga_pasar[3]
        ],

        "bbt": [
            gl.bobot_timbang,
            gl.bobot_rata_rata_timbang,
            gl.jumlah_sample_timbang,
            gl.jumlah_sample_timbang_kemarin,
            gl.average_daily_gain
        ]
        #"timestamp": datetime.now().isoformat()
    }

    json_besar_bobot = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "raw": gl.list_bobot_timbang
    }

    gl.json_thingspeak = json_besar
    gl.json_thingspeak_2 = json_besar_bobot
    
    # ----------------------- Simpan ke file -----------------------------
    #with open("sample_json_thg.json", "w") as f:
    #    json.dump(json_besar, f, separators=(",", ":"), ensure_ascii=False)

    #print("[pengolah_json] JSON besar berhasil disimpan ? sample_json_thg.json")
    


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
        
def kirim_thingspeak_2():
    pengolah_json()

    json_big = gl.json_thingspeak_2
    fields = split_json_to_fields(json_big)

    payload = {
        "api_key": WRITE_API_KEY_2,
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
        response = requests.post(THINGSPEAK_URL_2, data=payload)
        print("[ThingSpeak] Status:", response.text)
        response.close()
    except Exception as e:
        print("[ThingSpeak] ERROR:", e)

print("thingspeak.py dimuat.")