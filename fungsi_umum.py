import asyncio
import datetime
import time, json
from variabel_global import gl
from penyimpanan_data import simpan_data
import database_sqlite as db
import status_esp32
import requests
import serial,time
import serial.tools.list_ports

# fungsi_umum.py

_broadcast_callback = None
_loop = None


def register_broadcast_callback(callback, loop):
    global _broadcast_callback, _loop
    _broadcast_callback = callback
    _loop = loop


def broadcastkan():
    if _broadcast_callback and _loop:
        _loop.call_soon_threadsafe(
            lambda: asyncio.create_task(_broadcast_callback())
        )

def _serialize_dt(dt):
    if dt is None:
        return None
    if isinstance(dt, datetime.datetime):
        return dt.isoformat(sep=' ', timespec='microseconds')
    return str(dt)


def cek_null(v):
    """
    Return 0 jika variabel None, '' atau 0.
    Return 1 jika variabel ada nilainya.
    """
    if v is None:
        return 0
    if v == "":
        return 0
    if v == 0:
        return 0
    return 1


def connect_serial():
    """
    Mencoba menghubungkan serial tanpa blocking.
    Bila gagal ? tidak raise error.
    Bisa dipanggil berkali-kali dari async task.
    """

    # Jika sudah terhubung dan port masih valid ? tidak perlu reconnect
    if gl.ser is not None:
        if gl.ser.is_open:
            return gl.ser
        else:
            gl.ser = None  # port tertutup ? reset

    try:
        # Cari port yang cocok (opsional)
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            return None  # tidak ada port ? aman

        # Jika ada /dev/ttyUSB0 ? coba itu dulu
        target_port = None
        for p in ports:
            if "USB" in p or "ACM" in p:
                target_port = p
                break

        if target_port is None:
            return None  # tidak ada port cocok

        gl.ser = serial.Serial(target_port, 115200, timeout=0)
        print(f"[Serial] Terhubung ke {target_port}")
        return gl.ser

    except Exception:
        # gagal connect ? jangan hentikan python
        print("gagal terhubung ke serial")
        gl.ser = None
        return None



def baca_serial_nonblocking():
    """
    Membaca data dari serial tanpa blocking.
    Return:
        - string data jika ada
        - None jika tidak ada / port tidak tersedia
    """

    if gl.ser is None:
        return None  # port belum ada ? aman

    try:
        raw = gl.ser.readline()  # ini non-blocking jika timeout=0
        if not raw:
            return None

        data = raw.decode(errors="ignore").strip()

        return data if data else None

    except Exception:
        return None
    
def send_serial(text):
    """
    Kirim string ke ESP32 melalui serial.
    Aman untuk dipanggil kapan saja (non-blocking).
    """

    if gl.ser is None or not gl.ser.is_open:
        # Coba connect dulu
        connect_serial()
        if gl.ser is None:
            # Masih gagal ? jangan kirim apa pun
            print("[Serial] Belum terhubung, data tidak dikirim")
            return False

    try:
        # pastikan setiap paket berakhir newline ?
        gl.ser.write((text + "\n").encode())
        return True

    except Exception as e:
        print(f"[Serial] Error mengirim: {e}")
        gl.ser = None  # dianggap putus
        return False

import json

async def cek_serial():
    if gl.ser is None:
        connect_serial()
        return

    raw = baca_serial_nonblocking()
    if not raw:
        return

    try:
        # pastikan string
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")

        raw = raw.strip()

        data = json.loads(raw)   # ← INI KUNCI UTAMA

    except Exception as e:
        print("[ERROR] cek_serial:", e)
        print("[RAW DATA]", repr(raw))
        return

    # gl.kipas disinkronkan lewat status_esp32.py (cek generasi+boot_id
    # dulu, bukan ditimpa buta) - ACK Serial ini rawan race condition yang
    # sama persis dengan poll HTTP /kps: kalau ACK ini kebetulan datang
    # basi/telat, jangan sampai nimpa command yang lebih baru dari RPi.
    status_esp32.terapkan_status_kipas(data)
    gl.kipas_inspeksi[:5] = data["kpi"][:5]
    gl.kipas_saklar[:5] = data["kcs"][:5]
    gl.state_tanaman[:5] = data["stn"][:5]

    print("[ESP32]", data)


def atur_target(trgtsh, shmin=0, shmax=0):
    """Atur target suhu + batas minimal/maksimal otomatis."""
    gl.target_suhu = trgtsh/10
    # jika shmin tidak diberikan ? trgtsh - 30
    gl.suhu_minimal = shmin if shmin != 0 else trgtsh - 30
    # jika shmax tidak diberikan ? trgtsh + 30
    gl.suhu_maksimal = shmax if shmax != 0 else trgtsh + 30

def set_target():
    """Set target suhu berdasarkan usia ayam."""
    tabel_target = {
        0: 330,
        1: 325,
        2: 320,
        3: 318,
        4: 315,
        5: 310,
        6: 307,
        7: 305,
        8: 300,
        9: 298,
        10: 295,
        11: 294,
        12: 293,
        13: 292,
        14: 291,
        16: 290,
        17: 289,
        18: 288,
        19: 287,
        20: 286,
        21: 285,
        22: 284,
        23: 283,
        24: 282,
        25: 281,
        26: 280,
        27: 280,
        28: 280,
        29: 280,
        30: 280,
        31: 279,
        32: 278,
        33: 277,
        34: 276,
        35: 275,
        36: 275,
        37: 275,
        38: 275,
        39: 275,
        40: 275,
        41: 275,
        42: 275,
        43: 275,
        44: 275,
        45: 275,
    }

    if gl.usia_ayam in tabel_target:
        atur_target(tabel_target[gl.usia_ayam])
        print(f"[set_target] Usia {gl.usia_ayam} hari -> Target suhu {gl.target_suhu}°C")
    else:        
        print(f"[set_target] Usia {gl.usia_ayam} hari tidak ada di tabel, target suhu tidak diubah.")


import datetime

def _parse_dt_maybe(value):
    """Coba parse value ke datetime; bisa menerima datetime atau string."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        # coba beberapa format yang mungkin (ISO dengan mikrodetik / tanpa)
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.datetime.strptime(value, fmt)
            except ValueError:
                continue
        # coba datetime.fromisoformat (Python 3.7+)
        try:
            return datetime.datetime.fromisoformat(value)
        except Exception:
            pass
    # gagal parse
    return None

import datetime
import time

def tanggal_waktu_usia():
    """
    Menghitung usia ayam (hari bulat) dan hari_ke (desimal).
    Epoch hari dimulai dari jam 00:00.
    """
    #db.muat_konfigurasi_sqlite()  # pastikan data terbaru dari SQLite
    now = datetime.datetime.now()

    # =========================
    # Epoch & waktu realtime
    # =========================
    gl.epoch_data_waktu = int(time.time())

    gl.jam   = now.hour
    gl.menit = now.minute
    gl.detik = now.second
    gl.hari  = now.day
    gl.bulan = now.month
    gl.tahun = now.year

    gl.data_waktu = now.strftime("%H:%M:%S %d/%m/%Y")

    # =========================
    # Validasi tanggal masuk
    # =========================
    if not hasattr(gl, "tanggal_masuk_ayam") or gl.tanggal_masuk_ayam is None:
        print("[tanggal_waktu_usia] WARNING: tanggal_masuk_ayam belum diatur.")
        #gl.usia_ayam = 0
        #gl.hari_ke = 0.00
        return

    tanggal_masuk = _parse_dt_maybe(gl.tanggal_masuk_ayam)
    if tanggal_masuk is None:
        print("[tanggal_waktu_usia] WARNING: tidak bisa parse tanggal_masuk_ayam:", gl.tanggal_masuk_ayam)
        #gl.usia_ayam = 0
        #gl.hari_ke = 0.00
        return

    # =========================
    # Hitung berbasis MIDNIGHT
    # =========================
    today_midnight = now.replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    delta_midnight = today_midnight - tanggal_masuk

    # Usia ayam BULAT (ganti jam 00:00)
    gl.usia_ayam = max(0, delta_midnight.days)

    # =========================
    # Hari ke (desimal)
    # =========================
    # Detik sejak midnight hari ini
    detik_hari_ini = (
        now.hour * 3600 +
        now.minute * 60 +
        now.second
    )

    hari_ke_float = gl.usia_ayam + (detik_hari_ini / 86400.0)
    gl.hari_ke = float(f"{hari_ke_float:.2f}")

    # =========================
    # Simpan tanggal masuk pecahan
    # =========================
    gl.tanggal_masuk_ayam_tahun = tanggal_masuk.year
    gl.tanggal_masuk_ayam_bulan = tanggal_masuk.month
    gl.tanggal_masuk_ayam_hari  = tanggal_masuk.day

    # =========================
    # Persist & update target
    # =========================
    db.simpan_data_sqlite()
    set_target()
    broadcastkan()
    print(f"[tanggal_waktu_usia] Usia ayam: {gl.usia_ayam} hari | Hari ke: {gl.hari_ke}")

def atur_usia(hari_input: int):
    """
    Mengatur tanggal masuk ayam berdasarkan umur ayam saat ini.
    Epoch hari dimulai dari jam 00:00.
    """

    now = datetime.datetime.now()

    # Set ke awal hari (00:00)
    today_midnight = datetime.datetime(
        year=now.year,
        month=now.month,
        day=now.day,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    # Mundurkan sesuai umur ayam
    tanggal_masuk = today_midnight - datetime.timedelta(days=hari_input)

    # Simpan ke variabel global
    gl.tanggal_masuk_ayam = tanggal_masuk
    tanggal_waktu_usia()
    # Simpan permanen
    db.simpan_data_sqlite()
    broadcastkan()



# ======================================================
#  ?? OPSIONAL: FORMAT 2 DIGIT (seperti twoDigits di Arduino)
# ======================================================
def two_digits(value: int) -> str:
    """Mengubah angka menjadi string 2 digit, misal 7 -> '07'"""
    return f"{value:02d}"

HEALTHCHECK_URL = "https://hc-ping.com/7e11a194-6153-4bfe-827b-df05e5d48539"

def send_heartbeat():
    try:
        requests.get(HEALTHCHECK_URL, timeout=5)
    except requests.RequestException:
        pass


print("fungsi_umum.py dimuat.")