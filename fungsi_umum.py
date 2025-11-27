import asyncio
import datetime
import time
from variabel_global import gl
from penyimpanan_data import simpan_data

import serial,time
import serial.tools.list_ports


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


def atur_target(trgtsh, shmin=0, shmax=0):
    """Atur target suhu + batas minimal/maksimal otomatis."""
    gl.target_suhu = trgtsh
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


def atur_usia(hari_input: int):
    """
    Mengatur tanggal masuk ayam berdasarkan hari_input (umur ayam saat ini).
    """
    now = datetime.datetime.now()
    tanggal_masuk = now - datetime.timedelta(days=hari_input)

    # Simpan tanggal masuk ayam ke variabel global (as datetime)
    gl.tanggal_masuk_ayam = tanggal_masuk

    # Simpan permanen ke file JSON (sinkron)
    simpan_data()

    # Setelah itu, perbarui informasi waktu dan usia
    tanggal_waktu_usia()


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

def tanggal_waktu_usia():
    """
    Menghitung usia ayam dalam hari berdasarkan tanggal_masuk_ayam.
    Menyimpan hasil ke variabel global.
    """
    now = datetime.datetime.now()
    # Epoch timestamp (detik sejak 1 Jan 1970)
    gl.epoch_data_waktu = int(time.time())

    # Bagian-bagian waktu
    gl.jam   = now.hour
    gl.menit = now.minute
    gl.detik = now.second
    gl.hari  = now.day
    gl.bulan = now.month
    gl.tahun = now.year
    
    gl.data_waktu = now.strftime("%H:%M:%S %d/%m/%Y")

    # Pastikan gl.tanggal_masuk_ayam sudah diisi
    if not hasattr(gl, "tanggal_masuk_ayam") or gl.tanggal_masuk_ayam is None:
        gl.usia_ayam = 0
        return

    tanggal_masuk = _parse_dt_maybe(gl.tanggal_masuk_ayam)
    if tanggal_masuk is None:
        # can't parse ? set usia 0 atau handling khusus
        print("[tanggal_waktu_usia] WARNING: tidak bisa parse tanggal_masuk_ayam:", gl.tanggal_masuk_ayam)
        gl.usia_ayam = 0
        return

    delta = now - tanggal_masuk
    gl.usia_ayam = delta.days  # usia ayam dalam hari
    
    gl.tanggal_masuk_ayam_tahun = tanggal_masuk.year
    gl.tanggal_masuk_ayam_bulan = tanggal_masuk.month
    gl.tanggal_masuk_ayam_hari = tanggal_masuk.day

    simpan_data()
    set_target()


# ======================================================
#  ?? OPSIONAL: FORMAT 2 DIGIT (seperti twoDigits di Arduino)
# ======================================================
def two_digits(value: int) -> str:
    """Mengubah angka menjadi string 2 digit, misal 7 -> '07'"""
    return f"{value:02d}"



print("fungsi umum ok")
