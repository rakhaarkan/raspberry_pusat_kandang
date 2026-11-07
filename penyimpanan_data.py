import json,os
import asyncio
from variabel_global import gl
from pathlib import Path
from datetime import datetime
import copy

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

def _to_int_no_decimal(value,jumlah_angka=1):
    """Ubah float ke integer tanpa koma (x10)."""
    if value is None:
        return None
    try:
        return int(round(value * (10**jumlah_angka)))  # 33.7 -> 337
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
        "kipas": gl.kipas
    }
    
    #print(gl.last_saved_data)
    #print(data)
    # -----------------------------
    # CEK PERUBAHAN
    # -----------------------------
    if gl.last_saved_data is not None:
        if data == gl.last_saved_data:
            # Tidak ada perubahan
            print("[simpan_data] Tidak ada perubahan, file tidak disimpan.")
            return
    
    # -----------------------------
    # ADA PERUBAHAN ? SIMPAN
    # -----------------------------
    try:
        with open(FILE_PATH, "w") as f:
            json.dump(data, f, indent=2)

        # Update snapshot
        gl.last_saved_data = copy.deepcopy(data)

        print("[simpan_data] Data disimpan. kipas:", gl.kipas)

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
        if len(konfigurasi) >= 18:
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
                gl.jumlah_ayam_dipanen,
                gl.cek_proteksi_listrik,
                gl.flag_database_AI,
                gl.flag_alarm_siaga
            ) = konfigurasi[:18]

        print("[muat_data] Data berhasil dimuat")

    except Exception as e:
        print("[muat_data] ERROR parsing file:", e)

print("penyimpanan_data.py dimuat.")