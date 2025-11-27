import asyncio,time,serial,json
import variabel_global as gl
from penyimpanan_data import simpan_data, muat_data, LOCK_FILE
import thingspeak as thg
import fungsi_umum as fu
#from util_math import map_range, constrain
import RPi.GPIO as GPIO

wkt_kps = 0
LOCK_TIMER = asyncio.Lock()

# Setup GPIO mode
GPIO.setmode(GPIO.BCM)

# Inisialisasi GPIO untuk 5 relay kipas
RELAY_PINS = [16, 17, 18, 19, 21]
for pin in RELAY_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)  # atau HIGH tergantung logika relaymu

def map_range(x, in_min, in_max, out_min, out_max):
   return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def constrain(val, min_val, max_val):
    return max(min_val, min(max_val, val))

def kirim_json_kipas(k1, k2, k3, k4, k5):
    """
    Kirim state kipas ke ESP32 dalam format JSON.
    Non-blocking, aman.
    """
    data = {
        "kipas": [k1, k2, k3, k4, k5]
    }

    json_str = json.dumps(data)
    return fu.send_serial(json_str)


async def wajib_hidup(*args):
    """Menerima 5 argumen boolean (1 kipas = 1 argumen)"""
    async with gl.lock_kipas:
        for i, wajib in enumerate(args):
            if wajib:
                gl.kipas[i] = True
    print(f"Wajib hidup: {args}")
    await asyncio.sleep(0)

def saklar_kipas(k1, k2, k3, k4, k5):
    """Atur status 5 kipas (1=ON, 0=OFF) dengan sinkronisasi data dan penyimpanan"""
    #async with LOCK_FILE:
    kipas_state = [k1, k2, k3, k4, k5]
    gl.kipas = kipas_state

    for i in range(5):
        GPIO.output(RELAY_PINS[i], GPIO.HIGH if kipas_state[i] else GPIO.LOW)

    gl.status_relay = kipas_state
    print(f"Kipas diperbarui: {kipas_state}")
    
    kirim_json_kipas(k1, k2, k3, k4, k5)
    simpan_data()
    #thg.kirim_thingspeak()

def getWaktuSetelahDetik(detik):
    t = time.localtime(time.time() + detik)
    return f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}"

async def timer_kipas(jumlah_kipas: int):
    """Kontrol kipas otomatis (mode timer), berhenti otomatis jika mode kandang berubah."""
    async with LOCK_TIMER:
        # Jika bukan mode timer (mode 3), hentikan segera
        if gl.mode_kandang != 3:
            return

        gl.status_timer = 1
        sekarang = time.ticks_ms()

        durasi_hidup_ms = gl.waktu_hidup * 1000
        durasi_mati_ms = gl.waktu_mati * 60 * 1000

        # Hindari race condition
        if getattr(gl, "_sedang_update_timer", False):
            return
        gl._sedang_update_timer = True

        try:
            if gl.status_on_timer:
                if time.ticks_diff(sekarang, gl.waktuTerakhir) >= durasi_hidup_ms:
                    gl.status_on_timer = False
                    await saklar_kipas(0, 0, 0, 0, 0)
                    gl.waktuTerakhir = sekarang
                    gl.detail_timer_kipas = (
                        f"Hidup pada : {getWaktuSetelahDetik(gl.waktu_mati*60)} --- "
                        f"{gl.suhu_atas},{gl.suhu_outlet_atas},{gl.suhu_luar},{gl.suhu_acuan}"
                    )
                    await simpan_data()
            else:
                if time.ticks_diff(sekarang, gl.waktuTerakhir) >= durasi_mati_ms:
                    gl.status_on_timer = True
                    pola_kipas = {
                        1: (0, 0, 0, 1, 0),
                        2: (0, 1, 0, 1, 0),
                        3: (0, 1, 1, 1, 0),
                    }
                    await saklar_kipas(*pola_kipas.get(jumlah_kipas, (0, 0, 0, 0, 0)))
                    gl.waktuTerakhir = sekarang
                    gl.detail_timer_kipas = f"Mati pada : {getWaktuSetelahDetik(gl.waktu_hidup)}"
                    await simpan_data()
        finally:
            gl._sedang_update_timer = False

    await asyncio.sleep(0)

# --- Fungsi utama kontrol kipas ---
async def kontrol_kipas():
    # Debug / log status suhu
    gl.debug_str[0] = f"{gl.suhu_atas},{gl.suhu_outlet_atas},{gl.suhu_luar},{gl.suhu_acuan}"

    gl.keterangan_web = (
        f"Timer kipas : Hidup {gl.waktu_hidup} detik, "
        f"Mati {gl.waktu_mati} menit (diatur otomatis)"
    )

    gl.status_timer = 0

    # Logika mode kandang
    if gl.mode_kandang == 1:  # AUTO
        await setting_kipas_auto()

    elif gl.mode_kandang == 2:  # MANUAL
        await wajib_hidup(0, 0, 0, 0, 0)
        await saklar_kipas(*gl.kipas)

    elif gl.mode_kandang == 3:  # TIMER
        gl.status_timer = 1
        await wajib_hidup(0, 0, 0, 0, 0)
        await timer_kipas(gl.jumlah_kipas_timer)
        await saklar_kipas(*gl.kipas)

    elif gl.mode_kandang == 4:  # REMOTE / External control
        await wajib_hidup(0, 0, 0, 0, 0)
        await saklar_kipas(*gl.kipas)

    else:  # DEFAULT fallback
        await saklar_kipas(*gl.kipas)

async def pengatur_kipas_auto(wjb_hidup, *data_kipas):
    global wkt_kps
    sekarang = time.time() * 1000  # ms

    # Pastikan jeda minimal 1 detik antar eksekusi
    if sekarang - wkt_kps < 1000:
        return

    async with LOCK_AUTO:
        detail_kipas = []

        # === 1. Jalankan kipas wajib hidup ===
        dtl_wajib = []
        if len(wjb_hidup) == 5:
            wajib_list = [int(ch) for ch in wjb_hidup]
            aktif = [i+1 for i, val in enumerate(wajib_list) if val]
            await wajib_hidup(*wajib_list)
            dtl_wajib = aktif if aktif else [0]
        else:
            print("Error: Panjang wjb_hidup harus 5 karakter.")
            wajib_list = [0, 0, 0, 0, 0]
            dtl_wajib = [0]

        detail_kipas.append(f"0:{','.join(map(str, dtl_wajib))}")

        # === 2. Cari mode suhu terbaik (S) ===
        ambang_tertinggi = -999
        kipas_terbaik = [0, 0, 0, 0, 0]
        mode_dijalankan = False

        for i, item in enumerate(data_kipas):
            if not item or item == "N":
                continue

            bagian = item.split("-")
            mode = bagian[0]

            if mode == "S":
                ambang = float(bagian[1]) / 10.0
                kipas_str = bagian[2]
                kipas_list = [int(ch) for ch in kipas_str]

                detail_kipas.append(f"1:{int(ambang*10)},{','.join(str(i+1) for i,v in enumerate(kipas_list) if v)}")

                if gl.suhu_acuan > ambang and ambang > ambang_tertinggi:
                    ambang_tertinggi = ambang
                    kipas_terbaik = kipas_list

            elif mode == "T":
                ambang = float(bagian[1]) / 10.0
                jumlah_kipas = int(bagian[2])
                detail_kipas.append(f"2:{int(ambang*10)},{jumlah_kipas}")

        # Jalankan mode suhu terbaik
        if ambang_tertinggi > -999:
            await saklar_kipas(*kipas_terbaik)
            mode_dijalankan = True

        # === 3. Mode Timer (jika tidak ada mode suhu aktif) ===
        if not mode_dijalankan:
            for item in data_kipas:
                if not item or item == "N":
                    continue
                bagian = item.split("-")
                if bagian[0] != "T":
                    continue

                ambang = float(bagian[1]) / 10.0
                if gl.suhu_acuan > ambang:
                    jml_kipas = int(bagian[2])
                    suhu_min = int(bagian[3])
                    suhu_max = int(bagian[4])
                    wkt_hidup_min = int(bagian[5])
                    wkt_hidup_max = int(bagian[6])
                    wkt_mati_min = int(bagian[7])
                    wkt_mati_max = int(bagian[8])

                    sh_acuan = int(gl.suhu_acuan * 10)
                    gl.waktu_hidup = constrain(
                        map_range(sh_acuan, suhu_min, suhu_max, wkt_hidup_min, wkt_hidup_max),
                        wkt_hidup_min, wkt_hidup_max
                    )
                    gl.waktu_mati = constrain(
                        map_range(sh_acuan, suhu_min, suhu_max, wkt_mati_max, wkt_mati_min),
                        wkt_mati_min, wkt_mati_max
                    )

                    await timer_kipas(jml_kipas)
                    break

        # Simpan detail dan waktu terakhir
        gl.detail_kipas = "|".join(detail_kipas)
        wkt_kps = sekarang
        await simpan_data()

async def setting_kipas_auto():
    """Menentukan pengaturan kipas otomatis berdasarkan usia ayam."""
    usia = gl.usia_ayam

    # Daftar konfigurasi sesuai usia ayam
    # (setiap baris = pengaturan pengatur_kipas_auto)
    daftar_konfigurasi = {
        0:  ("00000", "T-290-1-290-350-10-60-10-40", "S-360-00010", "N", "N", "N"),
        1:  ("00000", "T-290-1-290-345-10-80-5-30", "S-345-00010", "N", "N", "N"),
        2:  ("00000", "T-280-2-285-340-10-90-5-25", "S-340-00010", "N", "N", "N"),
        3:  ("00000", "T-280-2-280-340-15-100-4-20", "S-340-00010", "N", "N", "N"),
        # ... dan seterusnya, bisa kamu lanjutkan sesuai tabel panjang di atas
    }

    # Ambil pengaturan sesuai usia
    konfigurasi = daftar_konfigurasi.get(usia)
    if konfigurasi:
        await pengatur_kipas_auto(*konfigurasi)
    else:
        await saklar_kipas(0, 0, 0, 1, 0)  # default aman
