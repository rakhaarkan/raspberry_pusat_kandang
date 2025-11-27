import sqlite3
from pathlib import Path
from datetime import datetime
from variabel_global import gl

db = sqlite3.connect("kandang_ayam.db")
cur = db.cursor()

DB_PATH = "kandang_ayam.db"

def _to_int_no_decimal(value):
    """Ubah float ke integer tanpa koma (x10)."""
    if value is None:
        return None
    try:
        return int(round(value * 10))  # 33.7 -> 337
    except:
        return None
    
def update_database_many(data_dict):
    jam = datetime.now().hour
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build SQL SET clause dynamically
    set_parts = [f"{key} = ?" for key in data_dict.keys()]
    set_clause = ", ".join(set_parts) + ", timestamp = ?"

    # Build value tuple
    values = list(data_dict.values())
    values.append(timestamp)  # add timestamp at the end
    values.append(jam)        # last param for WHERE jam = ?

    query = f"""
        UPDATE data_sensor
        SET {set_clause}
        WHERE jam = ?
    """

    # Single connection only
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        cur = conn.cursor()
        cur.execute(query, values)
        conn.commit()

    print(f"Updated jam {jam}: {data_dict}")

def update_db_sensor_24():
    update_database_many({
        "suhu_atas": gl.suhu_atas,
        "suhu_bawah": gl.suhu_bawah,
        "suhu_luar": gl.suhu_luar,
        "kelembapan_atas": gl.kelembapan_atas,
        "kelembapan_bawah": gl.kelembapan_bawah,
        "kelembapan_luar": gl.kelembapan_luar,
        "kwh_jam": gl.kwh_jam
    })
    
def baca_sql_sensor():
    """Baca data dari SQLite dan isi grafik gl.* mirip baca_json_sensor()."""

    # Jika database tidak ada ? kosongkan grafik
    if not Path(DB_PATH).exists():
        for i in range(1, 25):
            gl.grafik_suhu_atas[i]       = None
            gl.grafik_kelembapan_luar[i] = None
            gl.grafik_suhu_luar[i]       = None
            gl.grafik_kwh_listrik[i]     = None

        print("[baca_sql_sensor] DB tidak ditemukan, grafik dikosongkan.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Ambil semua 24 jam sekaligus
        cur.execute("SELECT jam, suhu_atas, suhu_luar, kelembapan_luar, kwh_jam FROM data_sensor")
        rows = cur.fetchall()

    except Exception as e:
        print("[baca_sql_sensor] ERROR membaca SQLite:", e)
        return
    finally:
        conn.close()

    # Isi grafik
    # Pastikan di-set None dulu
    for i in range(1, 24):
        gl.grafik_suhu_atas[i]       = None
        gl.grafik_kelembapan_luar[i] = None
        gl.grafik_suhu_luar[i]       = None
        gl.grafik_kwh_listrik[i]     = None

    # Masukkan data berdasarkan jam
    for row in rows:
        jam, suhu_atas, suhu_luar, kelembapan_luar, kwh_jam = row
        idx = int(jam) + 1  # karena grafik pakai index 1..24

        gl.grafik_suhu_atas[idx]       = _to_int_no_decimal(suhu_atas)
        gl.grafik_kelembapan_luar[idx] = _to_int_no_decimal(kelembapan_luar)
        gl.grafik_suhu_luar[idx]       = _to_int_no_decimal(suhu_luar)
        gl.grafik_kwh_listrik[idx]     = _to_int_no_decimal(kwh_jam)

    print("[baca_sql_sensor] Grafik diperbarui dari SQLite.")
