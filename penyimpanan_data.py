import json,os
import asyncio
from variabel_global import gl
from pathlib import Path
from datetime import datetime

FILE_PATH = Path("/home/rakha/Documents/Project_Kandang/data_state.json")
FILE_PATH_SENSOR = Path("/home/rakha/Documents/Project_Kandang/data_sensor.json")

LOCK_FILE = asyncio.Lock()  # lock untuk mencegah akses bersamaan ke file

def _serialize_dt(dt):
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat(sep=' ', timespec='microseconds')  # "YYYY-MM-DD HH:MM:SS.mmmmmm"
    # jika sudah string, kembalikan apa adanya
    return str(dt)

def load_data():
    """Load file JSON secara aman tanpa menghapus data lama."""
    if FILE_PATH_SENSOR.exists():
        try:
            with open(FILE_PATH_SENSOR, "r") as f:
                data = json.load(f)

                # Pastikan format benar
                if isinstance(data, dict):
                    return data
        except json.JSONDecodeError:
            print("[load_data] WARNING: File JSON rusak, menggunakan data kosong.")

        # Jika corrupt ? jangan membuat struktur 24 jam baru ? return {}
        return {}

    # Jika file belum ada ? buat struktur awal 24 jam
    return {str(i): {} for i in range(24)}

def save_data(data):
    with open(FILE_PATH_SENSOR, "w") as f:
        json.dump(data, f, indent=2)

def simpan_sensor():
    jam = datetime.now().hour
    jam_str = str(jam)

    data = load_data()

    # Pastikan slot jam adalah dict
    if jam_str not in data or not isinstance(data[jam_str], dict):
        data[jam_str] = {}

    # Update hanya field yang tersedia
    if gl.suhu_atas is not None:
        data[jam_str]["sha"] = gl.suhu_atas

    if gl.kelembapan_luar is not None:
        data[jam_str]["kll"] = gl.kelembapan_luar

    if gl.suhu_luar is not None:
        data[jam_str]["shl"] = gl.suhu_luar

    if gl.kwh_jam is not None:
        data[jam_str]["lst"] = gl.kwh_jam

    save_data(data)

    print(f"[simpan_sensor] Jam {jam} diperbarui ? {data[jam_str]}")

def _to_int_no_decimal(value):
    """Ubah float ke integer tanpa koma (x10)."""
    if value is None:
        return None
    try:
        return int(round(value * 10))  # 33.7 -> 337
    except:
        return None


def baca_json_sensor():
    """Baca data_sensor.json dan isi grafik gl.* dengan format tanpa koma."""

    # Jika file tidak ada ? kosongkan semua grafik
    if not FILE_PATH_SENSOR.exists():
        for i in range(1, 25):
            gl.grafik_suhu_atas[i] = None
            gl.grafik_kelembapan_luar[i] = None
            gl.grafik_suhu_luar[i] = None
            gl.grafik_kwh_listrik[i] = None
        print("[baca_json_sensor] File tidak ditemukan, grafik dikosongkan.")
        return

    # Load JSON
    try:
        with open(FILE_PATH_SENSOR, "r") as f:
            data = json.load(f)
    except Exception as e:
        print("[baca_json_sensor] ERROR membaca JSON:", e)
        return

    # Isi grafik 1..24
    for jam in range(24):
        idx = jam + 1  # indeks grafik
        jam_str = str(jam)

        row = data.get(jam_str, {})

        # Setiap nilai dikali 10 ? int
        gl.grafik_suhu_atas[idx]       = _to_int_no_decimal(row.get("sha"))
        gl.grafik_kelembapan_luar[idx] = _to_int_no_decimal(row.get("kll"))
        gl.grafik_suhu_luar[idx]       = _to_int_no_decimal(row.get("shl"))
        gl.grafik_kwh_listrik[idx]     = _to_int_no_decimal(row.get("lst"))

    print("[baca_json_sensor] Grafik diperbarui dari JSON (format tanpa koma).")



def simpan_data():
    data = {
        "kipas": gl.kipas,
        "konfigurasi": [
            gl.mode_kandang,
            gl.usia_ayam,
            _serialize_dt(gl.tanggal_masuk_ayam),
            gl.jumlah_kipas_timer,
            gl.waktu_hidup,
            gl.waktu_mati,
            gl.jumlah_ayam_awal,
            gl.jumlah_ayam_mati,
            gl.jumlah_pakan_sak,
            gl.bobot_rata_rata,
            gl.harga_kontrak_ayam,
            gl.harga_bibit_ayam,
            gl.harga_obat_ayam,
            gl.harga_pakan_kg,
            gl.jumlah_ayam_dipanen
        ]
    }

    try:
        with open(FILE_PATH, "w") as f:
            json.dump(data, f)
        print("[simpan_data] Data berhasil disimpan. kipas : ", gl.kipas)
    except Exception as e:
        print("[simpan_data] ERROR:", e)
        

def muat_data():
    if not FILE_PATH.exists():
        print("[muat_data] File tidak ditemukan")
        return

    try:
        with open(FILE_PATH, "r") as f:
            data = json.load(f)

        print("[muat_data] Data mentah:", data)

        # --- KIPAS ---
        kipas = data.get("kipas")
        if isinstance(kipas, list) and len(kipas) == 5:
            gl.kipas = kipas
        else:
            print("[muat_data] Kipas invalid, pakai default")

        # --- KONFIGURASI ---
        konfigurasi = data.get("konfigurasi", [])
        if len(konfigurasi) >= 15:
            (
                gl.mode_kandang,
                gl.usia_ayam,
                gl.tanggal_masuk_ayam,
                gl.jumlah_kipas_timer,
                gl.waktu_hidup,
                gl.waktu_mati,
                gl.jumlah_ayam_awal,
                gl.jumlah_ayam_mati,
                gl.jumlah_pakan_sak,
                gl.bobot_rata_rata,
                gl.harga_kontrak_ayam,
                gl.harga_bibit_ayam,
                gl.harga_obat_ayam,
                gl.harga_pakan_kg,
                gl.jumlah_ayam_dipanen
            ) = konfigurasi[:15]

        print("[muat_data] Data berhasil dimuat")

    except Exception as e:
        print("[muat_data] ERROR parsing file:", e)

